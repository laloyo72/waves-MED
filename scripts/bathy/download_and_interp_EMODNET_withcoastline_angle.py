#!/usr/bin/env python3

# We downloaded the coastline from EMODNET:
# https://downloads.emodnet-bathymetry.eu/v11/EMODnet_Bathymetry_2022_coastlines.zip
#
# This script downloads bathymetry from EMODnet and interpolates it
# to the SWAN computational grid (CGRID).
#
# The script supports rotated SWAN grids through the CGRID angle
# [alpinp], defined as:
#
#     direction of the positive x-axis of the input grid
#     in degrees, Cartesian convention.
#
# Example:
#
#     CGRID 347495 4545236 60 4000 6000 79 119 CIRCLE ...
#
# Here:
#     347495  -> X origin
#     4545236 -> Y origin
#     60      -> direction of positive x-axis (degrees)
#     4000    -> X length
#     6000    -> Y length
#     79      -> MX
#     119     -> MY
#
# LAST MODIFIED: @laloyo 08/09/2026
# -----------------------------------------------------------------------------


import sys
import numpy as np
import pandas as pd
import requests
import rioxarray
import utm
import os
import geopandas as gpd

from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from scipy.interpolate import LinearNDInterpolator


# =============================================================================
# 1. Read CGRID SWAN
# =============================================================================

def read_cgrid(cgrid_file):

    with open(cgrid_file, 'r') as f:

        for line in f:

            if line.strip().startswith("CGRID"):

                parts = line.split()

                # CGRID X0 Y0 ALP Xlen Ylen MX MY ...
                easting = float(parts[1])
                northing = float(parts[2])

                angle = float(parts[3])

                xlen = float(parts[4])
                ylen = float(parts[5])

                # SWAN specifies MX and MY as number of intervals.
                # Therefore number of grid points = MX + 1 and MY + 1.
                nx = int(parts[6]) + 1
                ny = int(parts[7]) + 1

                return (
                    easting,
                    northing,
                    angle,
                    xlen,
                    ylen,
                    nx,
                    ny
                )

    raise ValueError("CGRID definition not found in input file.")


# =============================================================================
# 2. Build rotated SWAN grid
# =============================================================================

def create_rotated_grid(
    easting,
    northing,
    angle,
    xlen,
    ylen,
    nx,
    ny
):
    """
    Create the SWAN computational grid taking into account CGRID [alpinp].

    SWAN defines [alpinp] as the direction of the positive x-axis
    of the input grid, in degrees, Cartesian convention.

    Therefore:

        x_axis = (cos(theta), sin(theta))

    and the positive y-axis is obtained by rotating x_axis +90 degrees:

        y_axis = (-sin(theta), cos(theta))

    The origin (easting, northing) corresponds to the SWAN grid origin.
    """

    theta = np.deg2rad(angle)

    # Local coordinates of the unrotated grid
    local_x = np.linspace(0.0, xlen, nx)
    local_y = np.linspace(0.0, ylen, ny)

    local_x, local_y = np.meshgrid(local_x, local_y)

    # Unit vectors of the SWAN grid
    x_axis = np.array([
        np.cos(theta),
        np.sin(theta)
    ])

    y_axis = np.array([
        -np.sin(theta),
        np.cos(theta)
    ])

    # Transform local SWAN coordinates to UTM coordinates
    grid_x = (
        easting
        + local_x * x_axis[0]
        + local_y * y_axis[0]
    )

    grid_y = (
        northing
        + local_x * x_axis[1]
        + local_y * y_axis[1]
    )

    return grid_x, grid_y


# =============================================================================
# 3. Calculate real UTM bounding box of rotated grid
# =============================================================================

def compute_rotated_grid_bbox(
    easting,
    northing,
    angle,
    xlen,
    ylen,
    zone_number,
    zone_letter,
    buffer_deg=0.05
):
    """
    Calculate the geographic bounding box of the complete rotated
    SWAN grid.

    This is important because simply using:

        xmin = easting
        xmax = easting + xlen

    is only correct for angle = 0 degrees.
    """

    theta = np.deg2rad(angle)

    # Four corners of the grid in local coordinates
    corners_local = np.array([
        [0.0, 0.0],
        [xlen, 0.0],
        [xlen, ylen],
        [0.0, ylen]
    ])

    # Rotation matrix corresponding to Cartesian angle
    rotation_matrix = np.array([
        [np.cos(theta), -np.sin(theta)],
        [np.sin(theta),  np.cos(theta)]
    ])

    # Rotate local coordinates
    corners_utm = corners_local @ rotation_matrix.T

    # Translate to UTM origin
    corners_utm[:, 0] += easting
    corners_utm[:, 1] += northing

    xmin = np.min(corners_utm[:, 0])
    xmax = np.max(corners_utm[:, 0])

    ymin = np.min(corners_utm[:, 1])
    ymax = np.max(corners_utm[:, 1])

    # Convert corners to lat/lon
    latitudes = []
    longitudes = []

    for x, y in corners_utm:

        lat, lon = utm.to_latlon(
            x,
            y,
            zone_number,
            zone_letter
        )

        latitudes.append(lat)
        longitudes.append(lon)

    lat_min = min(latitudes) - buffer_deg
    lat_max = max(latitudes) + buffer_deg

    lon_min = min(longitudes) - buffer_deg
    lon_max = max(longitudes) + buffer_deg

    print("\nRotated CGRID corners (UTM):")

    for i, (x, y) in enumerate(corners_utm):

        print(
            f"  Corner {i + 1}: "
            f"X = {x:.2f}, Y = {y:.2f}"
        )

    print("\nUTM bounding box:")
    print(f"  X: {xmin:.2f} -> {xmax:.2f}")
    print(f"  Y: {ymin:.2f} -> {ymax:.2f}")

    return lat_min, lat_max, lon_min, lon_max


# =============================================================================
# 4. UTM -> lat/lon
# =============================================================================

def utm_to_latlon(x, y, zone_number, zone_letter):

    lat, lon = utm.to_latlon(
        x,
        y,
        zone_number,
        zone_letter
    )

    return lat, lon


# =============================================================================
# 5. Download EMODnet GeoTIFF
# =============================================================================

def download_emodnet_geotiff(
    lat_min,
    lat_max,
    lon_min,
    lon_max,
    output_tif
):

    url = (
        "https://ows.emodnet-bathymetry.eu/wcs?"
        "SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&"
        "coverageId=emodnet:mean&FORMAT=image/tiff&"
        f"SUBSET=Lat({lat_min},{lat_max})&"
        f"SUBSET=Long({lon_min},{lon_max})"
    )

    print("\nRequesting EMODnet WCS:")
    print(url)

    r = requests.get(url)

    r.raise_for_status()

    with open(output_tif, "wb") as f:

        f.write(r.content)

    print(
        f"GeoTIFF EMODnet downloaded: "
        f"{output_tif}"
    )


# =============================================================================
# 6. Reproject to UTM
# =============================================================================

def reproject_to_utm(
    input_tif,
    output_tif_utm,
    utm_zone
):

    utm_crs = f"EPSG:326{utm_zone}"

    ds = rioxarray.open_rasterio(input_tif)

    ds_utm = ds.rio.reproject(utm_crs)

    ds_utm.rio.to_raster(output_tif_utm)

    print(
        f"GeoTIFF reprojected to UTM {utm_zone}: "
        f"{output_tif_utm}"
    )

    return output_tif_utm


# =============================================================================
# 7. GeoTIFF UTM -> points
# =============================================================================

def geotiff_to_points(
    bathy_tif_utm,
    output_points_file
):

    ds = rioxarray.open_rasterio(
        bathy_tif_utm
    )

    x = ds.x.values
    y = ds.y.values

    z = ds.values[0]

    points = []

    for i in range(len(y)):

        for j in range(len(x)):

            depth = float(z[i, j])

            if np.isnan(depth):
                continue

            points.append([
                x[j],
                y[i],
                depth
            ])

    df = pd.DataFrame(
        points,
        columns=[
            "x",
            "y",
            "depth"
        ]
    )

    df.to_csv(
        output_points_file,
        sep=" ",
        index=False,
        header=False
    )

    print(
        f"Bathymetry points saved to "
        f"{output_points_file}"
    )

    return df


# =============================================================================
# 8. Load EMODnet coastline
# =============================================================================

def load_emodnet_coastline(
    local_path,
    lat_min,
    lat_max,
    lon_min,
    lon_max,
    utm_zone
):

    print(
        "Loading EMODnet coastline "
        "from local shapefile..."
    )

    # Global coastline, EPSG:4326
    gdf = gpd.read_file(local_path)

    # Download bounding box in lat/lon
    domain_poly = Polygon([
        (lon_min, lat_min),
        (lon_max, lat_min),
        (lon_max, lat_max),
        (lon_min, lat_max)
    ])

    domain_gdf = gpd.GeoDataFrame(
        geometry=[domain_poly],
        crs="EPSG:4326"
    )

    # Clip coastline to download domain
    coast_clip = gpd.overlay(
        gdf,
        domain_gdf,
        how="intersection"
    )

    if coast_clip.empty:

        print(
            "Warning: clipped coastline is empty; "
            "using full domain polygon as land."
        )

        coast_utm = domain_gdf.to_crs(
            f"EPSG:326{utm_zone}"
        )

        land_polygon = unary_union(
            coast_utm.geometry
        )

        return land_polygon

    # Reproject coastline to UTM
    coast_utm = coast_clip.to_crs(
        f"EPSG:326{utm_zone}"
    )

    # Merge into single geometry
    land_polygon = unary_union(
        coast_utm.geometry
    )

    print(
        "Coastline clipped and "
        "reprojected successfully."
    )

    return land_polygon


# =============================================================================
# 9. Interpolate to CGRID with land mask
# =============================================================================

def interpolate_bathymetry_to_cgrid(
    bathy_df,
    grid_x,
    grid_y,
    land_polygon
):

    # -------------------------------------------------------------------------
    # Select water points only
    # -------------------------------------------------------------------------

    valid_points = np.array([

        (x, y, d)

        for x, y, d in zip(
            bathy_df["x"],
            bathy_df["y"],
            bathy_df["depth"]
        )

        if not land_polygon.contains(
            Point(x, y)
        )

    ])

    if len(valid_points) == 0:

        raise ValueError(
            "No valid water points for interpolation."
        )

    print(
        f"Number of valid water points: "
        f"{len(valid_points)}"
    )

    # -------------------------------------------------------------------------
    # Linear interpolation
    # -------------------------------------------------------------------------

    interpolator = LinearNDInterpolator(
        valid_points[:, :2],
        valid_points[:, 2]
    )

    interpolated_depths = interpolator(
        grid_x,
        grid_y
    )

    # -------------------------------------------------------------------------
    # Convert EMODnet negative depths to positive SWAN depths
    # -------------------------------------------------------------------------

    valid_depth_mask = (
        ~np.isnan(interpolated_depths)
        & (interpolated_depths < 0)
    )

    interpolated_depths[
        valid_depth_mask
    ] *= -1

    # -------------------------------------------------------------------------
    # Apply land mask
    #
    # SWAN:
    #     -1 = land / invalid
    # -------------------------------------------------------------------------

    for i in range(grid_x.shape[0]):

        for j in range(grid_x.shape[1]):

            point = Point(
                grid_x[i, j],
                grid_y[i, j]
            )

            if land_polygon.contains(point):

                interpolated_depths[i, j] = -1.0

    print(
        "Interpolation to CGRID completed."
    )

    return interpolated_depths


# =============================================================================
# 10. Save bathymetry coordinates
# =============================================================================

def save_bathymetry(
    output_file,
    grid_x,
    grid_y,
    depths
):

    with open(output_file, "w") as f:

        for i in range(depths.shape[0]):

            for j in range(depths.shape[1]):

                f.write(
                    f"{grid_x[i, j]:.6f} "
                    f"{grid_y[i, j]:.6f} "
                    f"{depths[i, j]:.2f}\n"
                )

    print(
        f"SWAN bathymetry saved to "
        f"{output_file}"
    )


# =============================================================================
# 11. Save bathymetry matrix
# =============================================================================

def save_bathymetry_matrix(
    output_file,
    depths
):

    # SWAN expects the matrix in the opposite
    # vertical ordering compared with the NumPy grid.
    depths_flipped = np.flipud(depths)

    np.savetxt(
        output_file,
        depths_flipped,
        fmt="%.2f"
    )

    print(
        f"SWAN depth matrix saved to "
        f"{output_file}"
    )


# =============================================================================
# 12. UTM zone utilities
# =============================================================================

def utm_zone_letter_from_lat(lat):

    letters = (
        "CDEFGHJKLMNPQRSTUVWX"
    )

    idx = int(
        (lat + 80) // 8
    )

    return letters[idx]


def utm_zone_from_lon(lon):

    return int(
        (lon + 180) // 6
    ) + 1


# =============================================================================
# 13. Main
# =============================================================================

if __name__ == "__main__":

    if len(sys.argv) < 5:

        print(
            "Usage: "
            "python3 script.py "
            "<case_name> "
            "<swan_case_name> "
            "<LAT> "
            "<LON>"
        )

        sys.exit(1)

    # -------------------------------------------------------------------------
    # Case and location
    # -------------------------------------------------------------------------

    case_name = sys.argv[1]

    swan_case_name = sys.argv[2]

    LAT = float(sys.argv[3])

    LON = float(sys.argv[4])

    # -------------------------------------------------------------------------
    # Automatically determine UTM zone
    # -------------------------------------------------------------------------

    utm_zone = utm_zone_from_lon(LON)

    utm_letter = (
        utm_zone_letter_from_lat(LAT)
    )

    print(
        f"Auto UTM zone/letter: "
        f"{utm_zone} {utm_letter}"
    )

    # -------------------------------------------------------------------------
    # SWAN input file
    # -------------------------------------------------------------------------

    cgrid_file = (
        f"../../cases/{case_name}/"
        f"input_{swan_case_name}.swn"
    )

    # -------------------------------------------------------------------------
    # Read CGRID
    # -------------------------------------------------------------------------

    (
        easting,
        northing,
        angle,
        xlen,
        ylen,
        nx,
        ny
    ) = read_cgrid(cgrid_file)

    print("\nCGRID:")

    print(
        f"  Origin X       : {easting}"
    )

    print(
        f"  Origin Y       : {northing}"
    )

    print(
        f"  Angle           : {angle} deg"
    )

    print(
        f"  X length        : {xlen} m"
    )

    print(
        f"  Y length        : {ylen} m"
    )

    print(
        f"  NX              : {nx}"
    )

    print(
        f"  NY              : {ny}"
    )

    # -------------------------------------------------------------------------
    # Create actual rotated SWAN grid
    # -------------------------------------------------------------------------

    grid_x, grid_y = create_rotated_grid(
        easting,
        northing,
        angle,
        xlen,
        ylen,
        nx,
        ny
    )

    # -------------------------------------------------------------------------
    # Calculate geographic bounding box of rotated grid
    # -------------------------------------------------------------------------

    (
        lat_min,
        lat_max,
        lon_min,
        lon_max
    ) = compute_rotated_grid_bbox(
        easting,
        northing,
        angle,
        xlen,
        ylen,
        utm_zone,
        utm_letter,
        buffer_deg=0.05
    )

    print("\nLat/Lon bbox:")
    print(
        f"  Latitude : "
        f"{lat_min} -> {lat_max}"
    )

    print(
        f"  Longitude: "
        f"{lon_min} -> {lon_max}"
    )

    # -------------------------------------------------------------------------
    # Bathymetry directory
    # -------------------------------------------------------------------------

    bathy_dir = (
        f"../../cases/{case_name}/bathy"
    )

    os.makedirs(
        bathy_dir,
        exist_ok=True
    )

    # -------------------------------------------------------------------------
    # Output files
    # -------------------------------------------------------------------------

    tif_raw = (
        f"{bathy_dir}/"
        f"emodnet_raw_{swan_case_name}.tif"
    )

    tif_utm = (
        f"{bathy_dir}/"
        f"emodnet_utm_{swan_case_name}.tif"
    )

    points_file = (
        f"{bathy_dir}/"
        f"bathy_points_utm_"
        f"{swan_case_name}.dat"
    )

    bottom_file = (
        f"{bathy_dir}/"
        f"bottom_{swan_case_name}.dat"
    )

    bottom_matrix_file = (
        f"{bathy_dir}/"
        f"bottom_{swan_case_name}_matrix.dat"
    )

    # -------------------------------------------------------------------------
    # Coastline
    # -------------------------------------------------------------------------

    coastline_path = (
        "../../DATA/coastline/"
        "Europe_coastline_2020_OSM/"
        "Europe_coastline_2020_OSM.shp"
    )

    # -------------------------------------------------------------------------
    # Download EMODnet
    # -------------------------------------------------------------------------

    download_emodnet_geotiff(
        lat_min,
        lat_max,
        lon_min,
        lon_max,
        tif_raw
    )

    # -------------------------------------------------------------------------
    # Reproject bathymetry to UTM
    # -------------------------------------------------------------------------

    reproject_to_utm(
        tif_raw,
        tif_utm,
        utm_zone
    )

    # -------------------------------------------------------------------------
    # Convert GeoTIFF to points
    # -------------------------------------------------------------------------

    bathy_df = geotiff_to_points(
        tif_utm,
        points_file
    )

    # -------------------------------------------------------------------------
    # Load coastline
    # -------------------------------------------------------------------------

    land_polygon = load_emodnet_coastline(
        coastline_path,
        lat_min,
        lat_max,
        lon_min,
        lon_max,
        utm_zone
    )

    # -------------------------------------------------------------------------
    # Interpolate bathymetry to rotated CGRID
    # -------------------------------------------------------------------------

    depths = interpolate_bathymetry_to_cgrid(
        bathy_df,
        grid_x,
        grid_y,
        land_polygon
    )

    # -------------------------------------------------------------------------
    # Save outputs
    # -------------------------------------------------------------------------

    save_bathymetry(
        bottom_file,
        grid_x,
        grid_y,
        depths
    )

    save_bathymetry_matrix(
        bottom_matrix_file,
        depths
    )

    # -------------------------------------------------------------------------
    # Finished
    # -------------------------------------------------------------------------

    print(
        "\nSWAN–EMODnet bathymetry "
        "pipeline completed."
    )
