# External datasets

Some datasets required by `waves-MED` are not included in the repository because of their size.

Please download them separately and place them in the following directories.

## Coastline

Download the Europe coastline shapefile and place its files in:

```text
DATA/coastline/Europe_coastline_2020_OSM/
```

The directory should contain:

```text
Europe_coastline_2020_OSM.dbf
Europe_coastline_2020_OSM.prj
Europe_coastline_2020_OSM.shp
Europe_coastline_2020_OSM.shx
```

Source: **[https://downloads.emodnet-bathymetry.eu/v11/EMODnet_Bathymetry_2022_coastlines.zip]**

## Bathymetry

The script automatically downloads the required bathymetry. The bathy/bathy_iberian_LR.nc file is used to make some simple plots. 

> These external datasets are intentionally excluded from Git to keep the repository lightweight.

