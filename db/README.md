# db

Stored data only; no code. The api finds this folder through the `SNOW_DB` environment variable (default: this folder), so in deployment it can be a mounted volume or, later, a real database.

| Path | Contents | In git? |
|---|---|---|
| `boundaries/` | Watershed boundaries, GeoJSON, lon/lat (EPSG:4326) | yes (small) |
| `fdl_store/` | Precomputed FDL/LDS rasters, written by `api/jobs/precompute_fdl.py` | no |
| `raw/` | Raw HDF download cache for download/comparison jobs and the terminal workbench; deleting it requires downloading again for threshold recalculation | no |
| `validation/woodruff/` | Original reference ZIP, validation reports, generated PC1 rasters and SHA256 manifest | no |

## Woodruff validation collection

The local collection is indexed by `validation/woodruff/README.md`.
Rebuild it from existing inputs with `api/jobs/Collect-WoodruffValidation.ps1`;
the script keeps originals and verifies copies by SHA256. Reports and code have
canonical versions under `Admin_And_Docs/Planning/` and `api/`. The collection
contains copies of the reports so the data and evidence can be reviewed together.

## Workbench inputs and outputs

The [terminal workbench](../api/README.md#interactive-terminal-workbench) uses
`boundaries/` and `raw/` under `SNOW_DB`. It processes daily observations rather
than reusing threshold-10 FDLs at other thresholds. Downloads are retained for
reuse (roughly 0.55 GB per tile-year for January through late August).
Workbench results are stored separately in `api/output/tui/<UTC timestamp>/`:
FDL/LDS GeoTIFFs, optional PC1, pixel CSV and settings/provenance JSON.
Changing `SNOW_DB` relocates inputs, not outputs. GUI threshold recalculation
requires the daily files to remain available. Synthetic mode creates no raw
satellite files. Keep generated data and raw HDFs out of git.

## Boundaries

`wbd_huc8_17050113.geojson`: South Fork Boise River, HUC8 17050113, 13 KB. USGS Watershed Boundary Dataset, fetched 2026-09-29 from `https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query?where=huc8='17050113'&outFields=huc8,name,areasqkm,states&outSR=4326&maxAllowableOffset=0.001&geometryPrecision=5&f=geojson` (simplified to about 100 m by the service). Use layer 5 with `huc10` or layer 6 with `huc12` for smaller units. Record the source, HUC code, fetch date and simplification for every boundary added.

## FDL store

One pair of files per tile, year and threshold:
- `fdl_<tile>_<year>_t<threshold>.tif`: first day land (DOY).
- `lds_<tile>_<year>_t<threshold>.tif`: last day snow (DOY).

Format: int16 GeoTIFF on the native MODIS sinusoidal grid (`+proj=sinu +R=6371007.181`, 463.31 m pixels, 2400 × 2400 per tile), deflate-compressed. Values: DOY; 0 = never snow or ocean; 365 = never melted; −1 = no data (nodata). Each file's tags record product, tile, year, threshold rule, start DOY, days used, missing DOYs, value codes, processing script and time.

Sizes (upper bound, uncompressed): about 11.5 MB per raster for MODIS. The 3 tiles that cover every HUC8 touching Idaho (h09v04, h10v04, h10v03) × 25 years of MODIS ≈ 1.7 GB for FDL + LDS at one threshold.

## SQLite chunk storage (November 10, 2026)

D18 is implemented for MOD10A1F Collection 6.1. `db/fdl_store/snow.sqlite3`
contains `products`, `runs`, and `chunks`: full tiles split into 200 × 200
arrays, zlib-compressed little-endian int16, indexed on the global pixel grid.
Each tile/year/threshold commits both FDL and LDS atomically. Missing chunks
raise an error; unknown, never-snow, and never-melted values remain distinct.
Boundaries remain GeoJSON files; VIIRS grid registration and ingestion are not
implemented. Product/collection is part of every storage key.

Run these commands from `api/` with the environment activated:

```bash
# Import existing full-tile FDL/LDS GeoTIFF pairs; retain originals.
python -m jobs.chunk_store import

# New precomputation downloads each tile-year once for all five thresholds.
python -m jobs.precompute_fdl --years 2021 2022 2023 --tiles h09v04
# For only one threshold:
python -m jobs.precompute_fdl --years 2021 2022 2023 --tiles h09v04 --threshold 10

# Export a layer for inspection (destination must not already exist).
python -m jobs.chunk_store export --tile h09v04 --year 2021 --kind FDL --output /tmp/fdl-2021.tif
```

`--thresholds 10 20 30` selects a subset; default is 10–50 in steps of 10.
Existing database runs are skipped; `--overwrite` replaces a tile/year/threshold
transactionally. Imports require full 2400 × 2400 int16 rasters with MODIS CRS,
alignment, nodata −1, and MOD10A1F v61 product tags. Both layers are read back
and compared exactly. Source tags and SHA256 hashes are retained as provenance.

The API automatically reads SQLite when `snow.sqlite3` exists. That database
is authoritative: import all wanted years before restarting the server; years
available only as GeoTIFFs will not appear. Without a database, the legacy
GeoTIFF reader still works. Restart the server after importing or overwriting
data because PCA results are cached in memory. Stop writers before copying
the database, or use SQLite's backup API to take a consistent live backup.

The local three-year pilot (h09v04, 2021–2023, threshold 10, FDL + LDS) used
864 chunks, 10,971,106 compressed payload bytes and an 11,526,144-byte database,
versus 69,120,000 bytes of raw int16 values. All imported values and the resulting
South Fork Boise PC1 matched the GeoTIFF path exactly. A warm local read of
three watershed windows took about 0.003 seconds; this is a pilot measurement,
not a deployment performance guarantee.
