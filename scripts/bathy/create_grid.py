# script to help you visualize the computational grid of your domain
# last modified on 18/09/2026
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

from pyproj import CRS, Transformer


# ============================================================
# CONFIGURATION
# ============================================================

BATHY_FILE = "../../DATA/bathy/bathy_iberian_LR.nc"


# ============================================================
# FUNCTIONS
# ============================================================

def get_utm_crs(lat, lon):
    """
    Determine the UTM CRS from a latitude/longitude position.
    """
    zone = int((lon + 180) / 6) + 1

    if lat >= 0:
        epsg = 32600 + zone
    else:
        epsg = 32700 + zone

    return CRS.from_epsg(epsg), zone


def latlon_to_utm(lat, lon):
    """
    Convert latitude/longitude to UTM coordinates.
    """
    utm_crs, zone = get_utm_crs(lat, lon)

    transformer = Transformer.from_crs(
        "EPSG:4326",
        utm_crs,
        always_xy=True
    )

    x, y = transformer.transform(lon, lat)

    return x, y, utm_crs, zone


def utm_to_latlon(x, y, utm_crs):
    """
    Convert UTM coordinates to latitude/longitude.
    """
    transformer = Transformer.from_crs(
        utm_crs,
        "EPSG:4326",
        always_xy=True
    )

    lon, lat = transformer.transform(x, y)

    return lon, lat


def plot_grid(
    ds,
    grid_lon,
    grid_lat,
    mxc,
    myc,
    show_grid=True
):
    """
    Plot bathymetry and computational grid.
    """

    lon_bathy = ds["lon"].values
    lat_bathy = ds["lat"].values

    elevation = ds["elevation"].values

    # Convert elevation to depth
    depth = -elevation

    fig, ax = plt.subplots(figsize=(11, 8))

    # --------------------------------------------------------
    # Bathymetry
    # --------------------------------------------------------

    mesh = ax.pcolormesh(
        lon_bathy,
        lat_bathy,
        depth,
        shading="auto",
    )

    cbar = plt.colorbar(mesh, ax=ax)
    cbar.set_label("Depth [m]")

    # --------------------------------------------------------
    # Computational grid
    # --------------------------------------------------------

    if show_grid:

        # Avoid drawing thousands of grid lines
        step_x = max(1, mxc // 50)
        step_y = max(1, myc // 50)

        # Grid lines in X direction
        for i in range(0, mxc + 1, step_x):
            ax.plot(
                grid_lon[:, i],
                grid_lat[:, i],
                linewidth=0.5,
                alpha=0.6
            )

        # Grid lines in Y direction
        for j in range(0, myc + 1, step_y):
            ax.plot(
                grid_lon[j, :],
                grid_lat[j, :],
                linewidth=0.5,
                alpha=0.6
            )

    # --------------------------------------------------------
    # Domain boundary
    # --------------------------------------------------------

    boundary_lon = [
        grid_lon[0, 0],
        grid_lon[0, -1],
        grid_lon[-1, -1],
        grid_lon[-1, 0],
        grid_lon[0, 0],
    ]

    boundary_lat = [
        grid_lat[0, 0],
        grid_lat[0, -1],
        grid_lat[-1, -1],
        grid_lat[-1, 0],
        grid_lat[0, 0],
    ]

    ax.plot(
        boundary_lon,
        boundary_lat,
        linewidth=2
    )

    # --------------------------------------------------------
    # Formatting
    # --------------------------------------------------------

    ax.set_xlabel("Longitude [°]")
    ax.set_ylabel("Latitude [°]")
    ax.set_title("SWAN computational grid")

    ax.set_aspect("equal")

    plt.tight_layout()
    plt.show()

def plot_grid2(
    ds,
    grid_lon,
    grid_lat,
    mxc,
    myc,
    show_grid=True
):
    """
    Plot bathymetry around the computational domain
    and overlay the SWAN computational grid.
    """

    # --------------------------------------------------------
    # Computational domain limits
    # --------------------------------------------------------

    grid_lon_min = np.nanmin(grid_lon)
    grid_lon_max = np.nanmax(grid_lon)

    grid_lat_min = np.nanmin(grid_lat)
    grid_lat_max = np.nanmax(grid_lat)

    # Add a margin around the computational domain
    margin_lon = 0.10 * (grid_lon_max - grid_lon_min)
    margin_lat = 0.10 * (grid_lat_max - grid_lat_min)

    plot_lon_min = grid_lon_min - margin_lon
    plot_lon_max = grid_lon_max + margin_lon

    plot_lat_min = grid_lat_min - margin_lat
    plot_lat_max = grid_lat_max + margin_lat

    # --------------------------------------------------------
    # Select only the relevant bathymetry
    # --------------------------------------------------------

    ds_plot = ds.sel(
        lon=slice(plot_lon_min, plot_lon_max),
        lat=slice(plot_lat_min, plot_lat_max)
    )

    lon_bathy = ds_plot["lon"].values
    lat_bathy = ds_plot["lat"].values

    elevation = ds_plot["elevation"].values

    # Convert elevation to depth
    depth = -elevation

    # --------------------------------------------------------
    # Plot
    # --------------------------------------------------------

    fig, ax = plt.subplots(figsize=(11, 8))

    mesh = ax.pcolormesh(
        lon_bathy,
        lat_bathy,
        depth,
        shading="auto"
    )

    ax.contourf(
        lon_bathy,
        lat_bathy,
        elevation,
        levels=[0, np.nanmax(elevation)],
        colors="black"
    )
    cbar = plt.colorbar(mesh, ax=ax)
    cbar.set_label("Depth [m]")

    # --------------------------------------------------------
    # Computational grid
    # --------------------------------------------------------

    if show_grid:

        # Avoid drawing thousands of grid lines
        step_x = max(1, mxc // 50)
        step_y = max(1, myc // 50)

        # Lines in X direction
        for i in range(0, mxc + 1, step_x):
            ax.plot(
                grid_lon[:, i],
                grid_lat[:, i],
                linewidth=0.5,
                alpha=0.6
            )

        # Lines in Y direction
        for j in range(0, myc + 1, step_y):
            ax.plot(
                grid_lon[j, :],
                grid_lat[j, :],
                linewidth=0.5,
                alpha=0.6
            )

    # --------------------------------------------------------
    # Domain boundary
    # --------------------------------------------------------

    boundary_lon = [
        grid_lon[0, 0],
        grid_lon[0, -1],
        grid_lon[-1, -1],
        grid_lon[-1, 0],
        grid_lon[0, 0],
    ]

    boundary_lat = [
        grid_lat[0, 0],
        grid_lat[0, -1],
        grid_lat[-1, -1],
        grid_lat[-1, 0],
        grid_lat[0, 0],
    ]

    ax.plot(
        boundary_lon,
        boundary_lat,
        linewidth=2
    )

    # --------------------------------------------------------
    # Set plot limits
    # --------------------------------------------------------

    ax.set_xlim(plot_lon_min, plot_lon_max)
    ax.set_ylim(plot_lat_min, plot_lat_max)

    # --------------------------------------------------------
    # Formatting
    # --------------------------------------------------------

    ax.set_xlabel("Longitude [°]")
    ax.set_ylabel("Latitude [°]")
    ax.set_title("SWAN computational grid")

    ax.set_aspect("equal")

    plt.tight_layout()
    plt.show()
# ============================================================
# MAIN PROGRAM
# ============================================================

print()
print("=" * 60)
print("        SWAN COMPUTATIONAL GRID GENERATOR")
print("=" * 60)
print()


# ============================================================
# 1. STUDY DOMAIN
# ============================================================

print("STEP 1 - DOMAIN ORIGIN")
print("-" * 60)

print(
    "Define the SOUTH-WEST corner of the computational domain."
)
print()

lat0 = float(input("Latitude  [deg]: "))
lon0 = float(input("Longitude [deg]: "))


# Convert to UTM
xpc, ypc, utm_crs, utm_zone = latlon_to_utm(
    lat0,
    lon0
)

print()
print(f"UTM zone: {utm_zone}")
print(f"X = {xpc:.3f} m")
print(f"Y = {ypc:.3f} m")


# ============================================================
# 2. DOMAIN SIZE
# ============================================================

print()
print("STEP 2 - DOMAIN SIZE")
print("-" * 60)

lx_km = float(
    input("Domain length in X [km]: ")
)

ly_km = float(
    input("Domain length in Y [km]: ")
)

lx = lx_km * 1000.0
ly = ly_km * 1000.0


# ============================================================
# 3. GRID RESOLUTION
# ============================================================

print()
print("STEP 3 - GRID RESOLUTION")
print("-" * 60)

dx_requested = float(
    input("Desired resolution in X [m]: ")
)

dy_requested = float(
    input("Desired resolution in Y [m]: ")
)


# Number of meshes
mxc = round(lx / dx_requested)
myc = round(ly / dy_requested)


# Recalculate actual resolution so that the
# requested domain size remains exact.
dx = lx / mxc
dy = ly / myc


# ============================================================
# 4. CREATE COMPUTATIONAL GRID
# ============================================================

x = xpc + np.arange(mxc + 1) * dx
y = ypc + np.arange(myc + 1) * dy

xx, yy = np.meshgrid(x, y)


# Convert all grid points back to lat/lon
grid_lon, grid_lat = utm_to_latlon(
    xx,
    yy,
    utm_crs
)


# ============================================================
# 5. LOAD BATHYMETRY
# ============================================================

print()
print("STEP 4 - LOADING BATHYMETRY")
print("-" * 60)

ds = xr.open_dataset(BATHY_FILE)

print()
print(f"Bathymetry file: {BATHY_FILE}")
print()

print(
    f"Bathymetry longitude: "
    f"{ds.lon.min().item():.3f} → {ds.lon.max().item():.3f}"
)

print(
    f"Bathymetry latitude:  "
    f"{ds.lat.min().item():.3f} → {ds.lat.max().item():.3f}"
)


# ============================================================
# 6. CHECK DOMAIN COVERAGE
# ============================================================

grid_lon_min = np.nanmin(grid_lon)
grid_lon_max = np.nanmax(grid_lon)

grid_lat_min = np.nanmin(grid_lat)
grid_lat_max = np.nanmax(grid_lat)

bathy_lon_min = ds.lon.min().item()
bathy_lon_max = ds.lon.max().item()

bathy_lat_min = ds.lat.min().item()
bathy_lat_max = ds.lat.max().item()


lon_ok = (
    grid_lon_min >= bathy_lon_min
    and
    grid_lon_max <= bathy_lon_max
)

lat_ok = (
    grid_lat_min >= bathy_lat_min
    and
    grid_lat_max <= bathy_lat_max
)


print()
print("Bathymetry coverage:")
print(
    f"  Longitude: {grid_lon_min:.3f} → "
    f"{grid_lon_max:.3f}"
)
print(
    f"  Latitude : {grid_lat_min:.3f} → "
    f"{grid_lat_max:.3f}"
)

print()

if lon_ok and lat_ok:
    print("✓ Bathymetry completely covers the computational domain.")
else:
    print(
        "⚠ WARNING: Bathymetry does NOT completely cover "
        "the computational domain!"
    )


# ============================================================
# 7. SWAN PARAMETERS
# ============================================================

alpc = 0.0

# Spectral parameters
mth = 72
fmin = 0.0345
fmax = 1.00
dfac = 34


# ============================================================
# 8. PRINT RESULTS
# ============================================================

print()
print("=" * 60)
print("              COMPUTATIONAL GRID")
print("=" * 60)

print()

print("Origin (SW corner):")
print(
    f"  Latitude  = {lat0:.6f}°"
)
print(
    f"  Longitude = {lon0:.6f}°"
)

print()

print("UTM:")
print(
    f"  Zone = {utm_zone}"
)
print(
    f"  X = {xpc:.3f} m"
)
print(
    f"  Y = {ypc:.3f} m"
)

print()

print("Domain:")
print(
    f"  X = {lx / 1000:.3f} km"
)
print(
    f"  Y = {ly / 1000:.3f} km"
)

print()

print("Grid:")
print(
    f"  Meshes in X = {mxc}"
)
print(
    f"  Meshes in Y = {myc}"
)

print(
    f"  Grid points = {mxc + 1} × {myc + 1}"
)

print()

print("Resolution:")
print(
    f"  dx = {dx:.3f} m"
)
print(
    f"  dy = {dy:.3f} m"
)

print()

print("SWAN CGRID:")
print()

print(
    f"CGRID "
    f"{xpc:.3f} "
    f"{ypc:.3f} "
    f"{alpc:.1f} "
    f"{lx:.3f} "
    f"{ly:.3f} "
    f"{mxc} "
    f"{myc} "
    f"CIRCLE "
    f"{mth} "
    f"{fmin} "
    f"{fmax} "
    f"{dfac}"
)

print()
print("=" * 60)


# ============================================================
# 9. PLOT
# ============================================================

print()
print("Generating plot...")

plot_grid2(
    ds,
    grid_lon,
    grid_lat,
    mxc,
    myc,
    show_grid=True
)
