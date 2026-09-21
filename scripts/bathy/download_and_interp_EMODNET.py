import numpy as np
import pandas as pd
import requests
import rioxarray
import utm
from scipy.interpolate import LinearNDInterpolator
from shapely.geometry import Polygon, Point

import sys

# ========================== 1. Leer CGRID SWAN ==========================

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
    raise ValueError("CGRID definition not found in the input file.")

# ========================== 2. UTM → lat/lon dominio ==========================

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

# ========================== 3. Descargar GeoTIFF EMODnet ==========================

def download_emodnet_geotiff(lat_min, lat_max, lon_min, lon_max, output_tif):
    url = (
        "https://ows.emodnet-bathymetry.eu/wcs?"
        "SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&"
        "coverageId=emodnet:mean&FORMAT=image/tiff&"
        f"SUBSET=Lat({lat_min},{lat_max})&"
        f"SUBSET=Long({lon_min},{lon_max})"
    )
    r = requests.get(url)
    r.raise_for_status()
    with open(output_tif, "wb") as f:
        f.write(r.content)
    print(f"GeoTIFF EMODnet descargado: {output_tif}")

# ========================== 4. Reproyectar a UTM ==========================

def reproject_to_utm(input_tif, output_tif_utm, utm_zone):
    utm_crs = f"EPSG:326{utm_zone}"
    ds = rioxarray.open_rasterio(input_tif)
    ds_utm = ds.rio.reproject(utm_crs)
    ds_utm.rio.to_raster(output_tif_utm)
    print(f"GeoTIFF reproyectado a UTM {utm_zone}: {output_tif_utm}")
    return output_tif_utm

# ========================== 5. GeoTIFF UTM → puntos x y depth ==========================

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
    print(f"Puntos de batimetría guardados en {output_points_file}")
    return df

# ========================== 6. Interpolación al CGRID SWAN ==========================

def interpolate_bathymetry_to_cgrid(bathy_df, easting, northing, xlen, ylen, nx, ny):
    grid_x = np.linspace(easting, easting + xlen, nx)
    grid_y = np.linspace(northing, northing + ylen, ny)
    grid_x, grid_y = np.meshgrid(grid_x, grid_y)

    # sin polígono de Mallorca: todo se considera agua
    valid_points = np.array([
        (x, y, d) for x, y, d in zip(bathy_df['x'], bathy_df['y'], bathy_df['depth'])
    ])

    if len(valid_points) == 0:
        raise ValueError("No valid points for interpolation.")

    interpolator = LinearNDInterpolator(valid_points[:, :2], valid_points[:, 2])
    interpolated_depths = interpolator(grid_x, grid_y)

    print("Interpolación al CGRID completada.")
    return grid_x, grid_y, interpolated_depths

def save_bathymetry(output_file, grid_x, grid_y, depths):
    with open(output_file, 'w') as f:
        for i in range(depths.shape[0]):
            for j in range(depths.shape[1]):
                f.write(f"{grid_x[i, j]:.6f} {grid_y[i, j]:.6f} {depths[i, j]:.2f}\n")
    print(f"Bathymetría SWAN guardada en {output_file}")

def save_bathymetry_matrix(output_file, depths):
    depths_flipped = np.flipud(depths)
    np.savetxt(output_file, depths_flipped, fmt="%.2f")
    print(f"Matriz de profundidad SWAN guardada en {output_file}")

# ========================== 7. Main ==========================

if __name__ == "__main__":
    # argumentos: case_name, swan_case_name, utm_zone, utm_letter
    case_name = sys.argv[1]
    swan_case_name = sys.argv[2]
    utm_zone = int(sys.argv[3])      # p.ej. 31
    utm_letter = sys.argv[4]        # p.ej. 'S'

    cgrid_file = f"../../cases/{case_name}/input_{swan_case_name}.swn"
    easting, northing, xlen, ylen, nx, ny = read_cgrid(cgrid_file)
    print("CGRID leído:", easting, northing, xlen, ylen, nx, ny)

    lat_min, lat_max, lon_min, lon_max = compute_latlon_bbox(
        easting, northing, xlen, ylen, utm_zone, utm_letter, buffer_deg=0.05
    )
    print("BBox lat/lon:", lat_min, lat_max, lon_min, lon_max)

    tif_raw = f"../../cases/{case_name}/bathy/emodnet_raw_{swan_case_name}.tif"
    tif_utm = f"../../cases/{case_name}/bathy/emodnet_utm_{swan_case_name}.tif"
    points_file = f"../../cases/{case_name}/bathy/bathy_points_utm_{swan_case_name}.dat"
    bottom_file = f"../../cases/{case_name}/bathy/bottom_{swan_case_name}.dat"
    bottom_matrix_file = f"../../cases/{case_name}/bathy/bottom_{swan_case_name}_matrix.dat"

    download_emodnet_geotiff(lat_min, lat_max, lon_min, lon_max, tif_raw)
    reproject_to_utm(tif_raw, tif_utm, utm_zone)
    bathy_df = geotiff_to_points(tif_utm, points_file)

    grid_x, grid_y, depths = interpolate_bathymetry_to_cgrid(
        bathy_df, easting, northing, xlen, ylen, nx, ny
    )

    save_bathymetry(bottom_file, grid_x, grid_y, depths)
    save_bathymetry_matrix(bottom_matrix_file, depths)

    print("Todo el flujo SWAN–EMODnet completado.")

