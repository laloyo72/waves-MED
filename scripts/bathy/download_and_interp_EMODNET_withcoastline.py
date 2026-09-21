# we downloaded the coastline from EMODNET: https://downloads.emodnet-bathymetry.eu/v11/EMODnet_Bathymetry_2022_coastlines.zip
# This script downloads bathymetry from EModnet and interpolates it to defined SWAN domain
# LAST MODIFIED: @laloyo 02/07/2026
# -------------------------------------------------------------------------------------------------------------------------------------
#!/usr/bin/env python3
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

# ========================== 1. Read CGRID SWAN ==========================

def read_cgrid(cgrid_file):
    with open(cgrid_file, 'r') as f:
        for line in f:
            if line.startswith("CGRID"):
                parts = line.split()
                easting = float(parts[1])
                northing = float(parts[2])
                xlen = float(parts[4])
                ylen = float(parts[5])
                nx = int(parts[6]) + 1
                ny = int(parts[7]) + 1
                return easting, northing, xlen, ylen, nx, ny
    raise ValueError("CGRID definition not found in input file.")

# ========================== 2. UTM → lat/lon bbox ==========================

def utm_to_latlon(x, y, zone_number, zone_letter):
    lat, lon = utm.to_latlon(x, y, zone_number, zone_letter)
    return lat, lon

def compute_latlon_bbox(easting, northing, xlen, ylen, zone_number, zone_letter, buffer_deg=0.05):
    xmin = easting
    xmax = easting + xlen
    ymin = northing
    ymax = northing + ylen

    lat_min, lon_min = utm_to_latlon(xmin, ymin, zone_number, zone_letter)
    lat_max, lon_max = utm_to_latlon(xmax, ymax, zone_number, zone_letter)

    lat_min -= buffer_deg
    lat_max += buffer_deg
    lon_min -= buffer_deg
    lon_max += buffer_deg

    return lat_min, lat_max, lon_min, lon_max

# ========================== 3. Download EMODnet GeoTIFF ==========================

def download_emodnet_geotiff(lat_min, lat_max, lon_min, lon_max, output_tif):
    url = (
        "https://ows.emodnet-bathymetry.eu/wcs?"
        "SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&"
        "coverageId=emodnet:mean&FORMAT=image/tiff&"
        f"SUBSET=Lat({lat_min},{lat_max})&"
        f"SUBSET=Long({lon_min},{lon_max})"
    )
    print(f"Requesting EMODnet WCS:\n{url}")
    r = requests.get(url)
    r.raise_for_status()
    with open(output_tif, "wb") as f:
        f.write(r.content)
    print(f"GeoTIFF EMODnet downloaded: {output_tif}")

# ========================== 4. Reproject to UTM ==========================

def reproject_to_utm(input_tif, output_tif_utm, utm_zone):
    utm_crs = f"EPSG:326{utm_zone}"
    ds = rioxarray.open_rasterio(input_tif)
    ds_utm = ds.rio.reproject(utm_crs)
    ds_utm.rio.to_raster(output_tif_utm)
    print(f"GeoTIFF reprojected to UTM {utm_zone}: {output_tif_utm}")
    return output_tif_utm

# ========================== 5. GeoTIFF UTM → points ==========================

def geotiff_to_points(bathy_tif_utm, output_points_file):
    ds = rioxarray.open_rasterio(bathy_tif_utm)
    x = ds.x.values
    y = ds.y.values
    z = ds.values[0]

    points = []
    for i in range(len(y)):
        for j in range(len(x)):
            depth = float(z[i, j])
            if np.isnan(depth):
                continue
            points.append([x[j], y[i], depth])

    df = pd.DataFrame(points, columns=["x", "y", "depth"])
    df.to_csv(output_points_file, sep=" ", index=False, header=False)
    print(f"Bathymetry points saved to {output_points_file}")
    return df

# ========================== 6. Load EMODnet coastline (local shapefile) ==========================

def load_emodnet_coastline(local_path, lat_min, lat_max, lon_min, lon_max, utm_zone):
    print("Loading EMODnet coastline from local shapefile...")
    gdf = gpd.read_file(local_path)  # global coastline, EPSG:4326

    # Domain polygon in lat/lon
    domain_poly = Polygon([
        (lon_min, lat_min),
        (lon_max, lat_min),
        (lon_max, lat_max),
        (lon_min, lat_max)
    ])
    domain_gdf = gpd.GeoDataFrame(geometry=[domain_poly], crs="EPSG:4326")

    # Clip coastline to domain
    coast_clip = gpd.overlay(gdf, domain_gdf, how="intersection")

    if coast_clip.empty:
        print("Warning: clipped coastline is empty; using full domain polygon as land.")
        coast_utm = domain_gdf.to_crs(f"EPSG:326{utm_zone}")
        land_polygon = unary_union(coast_utm.geometry)
        return land_polygon

    # Reproject to UTM
    coast_utm = coast_clip.to_crs(f"EPSG:326{utm_zone}")

    # Merge into single polygon
    land_polygon = unary_union(coast_utm.geometry)

    print("Coastline clipped and reprojected successfully.")
    return land_polygon

# ========================== 7. Interpolate to CGRID with land mask ==========================

def interpolate_bathymetry_to_cgrid(bathy_df, easting, northing, xlen, ylen, nx, ny, land_polygon):
    grid_x = np.linspace(easting, easting + xlen, nx)
    grid_y = np.linspace(northing, northing + ylen, ny)
    grid_x, grid_y = np.meshgrid(grid_x, grid_y)

    # water points only
    valid_points = np.array([
        (x, y, d) for x, y, d in zip(bathy_df['x'], bathy_df['y'], bathy_df['depth'])
        if not land_polygon.contains(Point(x, y))
    ])

    if len(valid_points) == 0:
        raise ValueError("No valid water points for interpolation.")

    interpolator = LinearNDInterpolator(valid_points[:, :2], valid_points[:, 2])
    interpolated_depths = interpolator(grid_x, grid_y)
    interpolated_depths[interpolated_depths < 0] *= -1

    # apply land mask: set depth = -1 on land
    for i in range(grid_x.shape[0]):
        for j in range(grid_x.shape[1]):
            if land_polygon.contains(Point(grid_x[i, j], grid_y[i, j])):
                interpolated_depths[i, j] = -1.0
    # convert EMODnet negative depths to SWAN positive depths
 #   interpolated_depths[interpolated_depths < 0] *= -1

    print("Interpolation to CGRID completed.")
    return grid_x, grid_y, interpolated_depths

# ========================== 8. Save outputs ==========================

def save_bathymetry(output_file, grid_x, grid_y, depths):
    with open(output_file, 'w') as f:
        for i in range(depths.shape[0]):
            for j in range(depths.shape[1]):
                f.write(f"{grid_x[i, j]:.6f} {grid_y[i, j]:.6f} {depths[i, j]:.2f}\n")
    print(f"SWAN bathymetry saved to {output_file}")

def save_bathymetry_matrix(output_file, depths):
    depths_flipped = np.flipud(depths)
    np.savetxt(output_file, depths_flipped, fmt="%.2f")
    print(f"SWAN depth matrix saved to {output_file}")
# ==================== extra: definition of utm zone ===================
def utm_zone_letter_from_lat(lat):
    letters = "CDEFGHJKLMNPQRSTUVWX"
    idx = int((lat + 80) // 8)
    return letters[idx]

def utm_zone_from_lon(lon):
    return int((lon + 180) // 6) + 1
# ========================== 9. Main ==========================

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python3 script.py <case_name> <swan_case_name> <utm_zone> <utm_letter>")
        sys.exit(1)
    
    # we define case and lat,lon in the main operational script

    case_name = sys.argv[1]
    swan_case_name = sys.argv[2]
    LAT = float(sys.argv[3])
    LON = float(sys.argv[4])

    utm_zone = utm_zone_from_lon(LON)
    utm_letter = utm_zone_letter_from_lat(LAT)

    print(f"Auto UTM zone/letter: {utm_zone} {utm_letter}")

    cgrid_file = f"../../cases/{case_name}/input_{swan_case_name}.swn"
    easting, northing, xlen, ylen, nx, ny = read_cgrid(cgrid_file)
    print("CGRID:", easting, northing, xlen, ylen, nx, ny)

    lat_min, lat_max, lon_min, lon_max = compute_latlon_bbox(
        easting, northing, xlen, ylen, utm_zone, utm_letter, buffer_deg=0.05
    )
    print("Lat/Lon bbox:", lat_min, lat_max, lon_min, lon_max)

    bathy_dir = f"../../cases/{case_name}/bathy"
    os.makedirs(bathy_dir, exist_ok=True)
    
    tif_raw = f"{bathy_dir}/emodnet_raw_{swan_case_name}.tif"
    tif_utm = f"{bathy_dir}/emodnet_utm_{swan_case_name}.tif"
    points_file = f"{bathy_dir}/bathy_points_utm_{swan_case_name}.dat"
    bottom_file = f"{bathy_dir}/bottom_{swan_case_name}.dat"
    bottom_matrix_file = f"{bathy_dir}/bottom_{swan_case_name}_matrix.dat"

    coastline_path = "../../DATA/coastline/Europe_coastline_2020_OSM/Europe_coastline_2020_OSM.shp"

    download_emodnet_geotiff(lat_min, lat_max, lon_min, lon_max, tif_raw)
    reproject_to_utm(tif_raw, tif_utm, utm_zone)
    bathy_df = geotiff_to_points(tif_utm, points_file)

    land_polygon = load_emodnet_coastline(
        coastline_path,
        lat_min, lat_max,
        lon_min, lon_max,
        utm_zone
    )

    grid_x, grid_y, depths = interpolate_bathymetry_to_cgrid(
        bathy_df, easting, northing, xlen, ylen, nx, ny, land_polygon
    )

    save_bathymetry(bottom_file, grid_x, grid_y, depths)
    save_bathymetry_matrix(bottom_matrix_file, depths)

    print("SWAN–EMODnet bathymetry pipeline completed.")

