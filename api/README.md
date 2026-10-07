# api

All Python for the project: the science, the precompute jobs, and (later) the web server. Stored data lives in [`../db/`](../db/README.md), not here.

| Folder | Contents |
|---|---|
| `snow/` | The science. `fdl.py`: FDL/LDS from daily NDSI codes. `watershed.py`: MODIS grid, boundary masks, GeoTIFF export. `matrix.py`: rasters → D matrix and back. `pca.py`: PCA, PC1. `synthetic.py`: synthetic FDL stacks for tests. |
| `jobs/` | Offline scripts. `download.py`: fetch raw MOD10A1F files. `precompute_fdl.py`: download, compute FDL, keep only the rasters. `run_real.py`: end-to-end check on one watershed (raw files → FDL → PC1 map + GeoTIFF). These may later become their own background service. |
| `server/` | Web server. Not started; see [`server/README.md`](server/README.md). |
| `tests/` | pytest suite. |
| `config.py` | Where stored data is: `SNOW_DB` environment variable, default `../db`. |

## Setup

Run everything from this folder (`api/`).

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt      # Windows
.venv/bin/pip install -r requirements.txt          # macOS / Linux
```

Checked on Windows 11 with Python 3.12 (2026-10-06): all packages install from pip, including `pyhdf`.

## Tests

```
.venv\Scripts\python -m pytest
```

What they check (26 tests, all passing on 2026-10-06):
- `test_fdl.py`: one hand-built pixel per FDL rule (forward and backward search, cloud gaps, returning snow, inland water, ocean, never melted, never snow, never observed, the threshold edge, and the known start-day quirk). Also that row-strip processing gives the same result as the whole tile.
- `test_reference.py`: runs Woodruff's starter code (`../reference/`) on a synthetic season and checks `snow/fdl.py` matches it on every pixel. The one intended difference: never-observed pixels are 0 there and −1 here. Needs `xarray` and `rioxarray`; skipped without them.
- `test_matches_archive.py`: the copies in `snow/` give identical output to the originals in `../archive/`.
- `test_pca.py`: PC1 recovers the synthetic true pattern (r > 0.99) with covariance and correlation PCA; sign rule.
- `test_watershed.py`: South Fork Boise mask = 15,741 pixels (center rule) / 16,422 (all touched), area within 1% of WBD, one tile (h09v04).

## Jobs

Need an Earthdata login (free account at https://urs.earthdata.nasa.gov/). The scripts try the `EARTHDATA_TOKEN` environment variable (see [`../get_EarthData_Access.md`](../get_EarthData_Access.md)), then `~/.netrc`, and never prompt. To create `~/.netrc` once:
```
.venv\Scripts\python -c "import earthaccess; earthaccess.login(persist=True)"
```
Never commit tokens, passwords or `.netrc`.

**Precompute FDL** (the main path: nothing raw is kept):
```
.venv\Scripts\python -m jobs.precompute_fdl --years 2020 2021 2022 2023 2024 --tiles h09v04 h10v04
```
- Per tile-year: lists the granules in NASA's catalog, downloads them in parallel (`--workers`, default 8), checks each against the catalog's byte size and SHA256 (5 retries), reads `CGF_NDSI_Snow_Cover` into memory and deletes the file.
- Writes `db/fdl_store/fdl_<tile>_<year>_t<threshold>.tif` and `lds_...tif`: int16, native MODIS grid, with provenance tags.
- About 0.55 GB downloaded per tile-year, a few MB kept; about 2.5 GB RAM. Finished tile-years are skipped; `--overwrite` recomputes. If any day fails after retries, nothing is written for that tile-year.
- Not yet run against real NSIDC downloads (the parts below the download were tested on local HDF files).

**Download raw files** (only needed for `run_real.py`): `python -m jobs.download --years 2020 2021 --tile h09v04`. Files go to `db/raw/` (gitignored, safe to delete).

**End-to-end check:** `python -m jobs.run_real --years 2020 2021 2022 2023 2024`. Defaults to South Fork Boise (HUC8 17050113) from `db/boundaries/`. Options: `--geojson`, `--threshold`, `--start-doy`, `--correlation`. Writes to `api/output/` (gitignored). Refuses watersheds spanning two tiles. Known issue: on Windows the figure step crashes (`%-d` in a date format, `run_real.py` `_doy_label`); the GeoTIFFs are written before that.

## `snow/fdl.py` vs. the starter code

Same algorithm as `../reference/Starter_Code_FDL_LDS_MOD10A1F.py` (start on DOY 91; search forward for pixels that are snow that day, backward for pixels that are clear; returning snow ignored). Changes:
- Reads `CGF_NDSI_Snow_Cover` by name as raw uint8 with `pyhdf`, so fill and missing codes stay codes instead of becoming NaN (which gave FDL = 0).
- Raises if the HDF grid metadata can't be parsed, instead of falling back to the h00v00 origin.
- Pixels never observed as snow or clear get −1 (no data), kept apart from 0 (never snow) and 365 (never melted).

Not changed: the start-day FDL for pixels missing on DOY 91 (ask Woodruff), 365 in leap years, ocean = 0, and LDS ignoring `Cloud_Persistence`.

## Conventions

PCA is covariance by default with `use_correlation=True` available (D06 open); scores are the uncentered projection; the sign is flipped so higher PC1 = later melt; pixels with 0, 365 or −1 in any year are dropped before PCA. Details in [`../CLAUDE.md`](../CLAUDE.md) and the [decision register](../Admin_And_Docs/Planning/decisions.md).

History: the first real-data results (South Fork Boise 2020–2024), timings and the data-access findings are in [`../archive/realdata/README.md`](../archive/realdata/README.md).
