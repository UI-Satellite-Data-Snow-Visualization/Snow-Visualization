# db

Stored data only; no code. The api finds this folder through the `SNOW_DB` environment variable (default: this folder), so in deployment it can be a mounted volume or, later, a real database.

| Path | Contents | In git? |
|---|---|---|
| `boundaries/` | Watershed boundaries, GeoJSON, lon/lat (EPSG:4326) | yes (small) |
| `fdl_store/` | Precomputed FDL/LDS rasters, written by `api/jobs/precompute_fdl.py` | no |
| `raw/` | Raw HDF download cache for `api/jobs/download.py` and `run_real.py`; safe to delete | no |

## Boundaries

`wbd_huc8_17050113.geojson`: South Fork Boise River, HUC8 17050113, 13 KB. USGS Watershed Boundary Dataset, fetched 2026-09-29 from `https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query?where=huc8='17050113'&outFields=huc8,name,areasqkm,states&outSR=4326&maxAllowableOffset=0.001&geometryPrecision=5&f=geojson` (simplified to about 100 m by the service). Use layer 5 with `huc10` or layer 6 with `huc12` for smaller units. Record the source, HUC code, fetch date and simplification for every boundary added.

## FDL store

One pair of files per tile, year and threshold:
- `fdl_<tile>_<year>_t<threshold>.tif`: first day land (DOY).
- `lds_<tile>_<year>_t<threshold>.tif`: last day snow (DOY).

Format: int16 GeoTIFF on the native MODIS sinusoidal grid (`+proj=sinu +R=6371007.181`, 463.31 m pixels, 2400 × 2400 per tile), deflate-compressed. Values: DOY; 0 = never snow or ocean; 365 = never melted; −1 = no data (nodata). Each file's tags record product, tile, year, threshold rule, start DOY, days used, missing DOYs, value codes, processing script and time.

Sizes (upper bound, uncompressed): about 11.5 MB per raster for MODIS. The 3 tiles that cover every HUC8 touching Idaho (h09v04, h10v04, h10v03) × 25 years of MODIS ≈ 1.7 GB for FDL + LDS at one threshold.
