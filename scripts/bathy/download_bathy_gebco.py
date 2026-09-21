import xarray as xr

# URL OPeNDAP gebco
url = "https://dap.ceda.ac.uk/thredds/dodsC/bodc/gebco/global/gebco_2024/sub_ice_topography_bathymetry/netcdf/GEBCO_2024_sub_ice_topo.nc"

ds = xr.open_dataset(url)
print("data min/max longitude", ds['lon'].min().values, ds['lon'].max().values)
print("data min/max latitude", ds['lat'].min().values, ds['lat'].max().values)

# vars
lat_var = 'lat'
lon_var = 'lon'
batim_var = 'elevation'

# domain -- iberian peninsula
lat_min = 34
lat_max = 45
lon_min = -11
lon_max = 5

subset = ds[batim_var].sel(
    lat=slice(lat_min, lat_max),
    lon=slice(lon_min, lon_max)
)

output_path = "../../DATA/bathy/bathy_iberian_LR.nc"
subset.to_netcdf(f"{output_path}")

print(f"bathy saved :3 in {output_path}")

