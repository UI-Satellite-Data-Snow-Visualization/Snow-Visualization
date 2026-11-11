# db

Stored data only; no code. The api finds this folder through the `SNOW_DB` environment variable (default: this folder), so in deployment it can be a mounted volume or, later, a real database.

| Path | Contents | In git? |
|---|---|---|
| `boundaries/` | Watershed boundaries, GeoJSON, lon/lat (EPSG:4326) | yes (small) |
| `fdl_store/` | `snow.sqlite3`: precomputed FDL/LDS for MODIS and VIIRS, written by `api/jobs/precompute_fdl.py` (legacy GeoTIFF pairs may also exist) | no |
| `raw/` | Raw daily files (MODIS `.hdf`, VIIRS `.h5`) for download/comparison jobs and the terminal workbench, plus NASA's day lists (`<SHORTNAME>_<tile>_<year>_catalog.json`); deleting it requires downloading again for threshold recalculation | no |
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
reuse (roughly 0.55 GB per tile-year for MODIS and 1 GB for VIIRS, January
through late August).
Workbench results are stored separately in `api/output/tui/<UTC timestamp>/`:
FDL/LDS GeoTIFFs, optional PC1, pixel CSV and settings/provenance JSON.
Changing `SNOW_DB` relocates inputs, not outputs. GUI threshold recalculation
requires the daily files to remain available. Synthetic mode creates no raw
satellite files. Keep generated data and raw HDFs out of git.

## Boundaries

`wbd_huc8_17050113.geojson`: South Fork Boise River, HUC8 17050113, 13 KB. USGS Watershed Boundary Dataset, fetched 2026-09-29 from `https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query?where=huc8='17050113'&outFields=huc8,name,areasqkm,states&outSR=4326&maxAllowableOffset=0.001&geometryPrecision=5&f=geojson` (simplified to about 100 m by the service). Use layer 5 with `huc10` or layer 6 with `huc12` for smaller units. Record the source, HUC code, fetch date and simplification for every boundary added.

## Legacy GeoTIFF FDL store (MODIS only)

Before the SQLite store (below), and still readable when no `snow.sqlite3` exists. One pair of files per tile, year and threshold:
- `fdl_<tile>_<year>_t<threshold>.tif`: first day land (DOY).
- `lds_<tile>_<year>_t<threshold>.tif`: last day snow (DOY).

Format: int16 GeoTIFF on the native MODIS sinusoidal grid (`+proj=sinu +R=6371007.181`, 463.31 m pixels, 2400 × 2400 per tile), deflate-compressed (predictor 2, tiled). Values: DOY; 0 = never snow or ocean; 365 = never melted; −1 = no data (nodata). Each file's tags record product, tile, year, threshold rule, start DOY, days used, missing DOYs, value codes, processing script and time.

Size (measured 2026-11-03): a deflate-compressed FDL + LDS pair is about 4.1–4.7 MB per tile-year and threshold (23 MB uncompressed), measured on h09v04 and h10v04 for 2013 and 2016 at thresholds 10–50.

## SQLite chunk storage (November 10, 2026)

D18 is implemented for MOD10A1F Collection 6.1 and, since the same day, VIIRS
VNP10A1F.002 and VJ110A1F.002 (3000 × 3000 tiles: 225 chunks per layer, 450 per
tile-year and threshold). `db/fdl_store/snow.sqlite3`
contains `products`, `runs`, and `chunks`: full tiles split into 200 × 200
arrays, zlib-compressed little-endian int16, indexed on the global pixel grid.
Each tile/year/threshold commits both FDL and LDS atomically. Missing chunks
raise an error; unknown, never-snow, and never-melted values remain distinct.
Boundaries remain GeoJSON files. Product/collection is part of every storage key,
and each product's grid is registered in the `products` table. Add
`--product viirs` to the precompute and export commands below for VIIRS.

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

### Sizes in the SQLite store

From two real runs:
- **MODIS:** the pilot above stored 3 tile-years at one threshold in 11.5 MB, about **3.8 MB per tile-year and threshold** (FDL + LDS).
- **VIIRS:** `precompute_fdl --product viirs --years 2023 2024 --tiles h09v04`, all five thresholds, made a 64.6 MB database (2026-11-11), about **6.5 MB per tile-year and threshold**. VIIRS tiles have 1.56× MODIS's pixels.

For the 3 tiles that cover every HUC8 touching Idaho (h09v04, h10v04, h10v03):

| Stored | MODIS, 26 years (2000–2025) | VIIRS Suomi NPP, 14 years (2012–2025) | Each new year adds (MODIS + VIIRS) |
|---|---|---|---|
| 1 threshold (10) | about 0.30 GB | about 0.27 GB | about 31 MB |
| 5 thresholds (10–50, the default) | about 1.5 GB | about 1.4 GB | about 155 MB |

Higher thresholds compress slightly worse (their maps are noisier), so sizes vary by threshold. The server reads only FDL (`api/snow/store.py`), joining tiles for watersheds that span more than one, so multi-tile watersheds need no separate stitching. LDS is stored but not read yet; storing FDL only would roughly halve these sizes.

### Compute memory (measured 2026-11-03, macOS, MODIS)

For one full MODIS tile-year held in memory (243 daily uint8 layers, about 1.4 GB), FDL computed in 400-row strips peaked at **3.4 GB RAM for one threshold** (about 2 s of calculation). **Ten thresholds computed from the same loaded data peaked at 3.8 GB** (about 20 s). Downloading and reading the daily files dominate and happen once per tile-year, however many thresholds are computed. At the ~13 MB/s measured earlier, that's about 0.55 GB and 40 s for MODIS, and about 1 GB for VIIRS (0.98 GB measured for h09v04 2023). That's why `precompute_fdl.py` computes all five thresholds from one download. A VIIRS daily stack is about 2.2 GB (3000 × 3000); its peak RAM hasn't been measured.
