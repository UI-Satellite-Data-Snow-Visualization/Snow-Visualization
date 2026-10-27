# api

All Python for the project: the science, local workbench, precompute jobs, and
(later) the web server. Stored inputs live in [`../db/`](../db/README.md);
generated experiment outputs go to `api/output/` (gitignored).

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

CI (`../.github/workflows/ci.yml`) runs these on Ubuntu, Windows and macOS on every push to any branch and on every PR, plus a ruff check for real errors (undefined names, unused imports). To run the same check locally: `pip install ruff`, then `ruff check --select E9,F --exclude archive,reference .` from the repo root.

```
.venv\Scripts\python -m pytest
```

Original science suite (26 tests recorded passing on 2026-10-06):
- `test_fdl.py`: one hand-built pixel per FDL rule (forward and backward search, cloud gaps, returning snow, inland water, ocean, never melted, never snow, never observed, the threshold edge, and the known start-day quirk). Also that row-strip processing gives the same result as the whole tile.
- `test_reference.py`: runs Woodruff's starter code (`../reference/`) on a synthetic season and checks `snow/fdl.py` matches it on every pixel. The one intended difference: never-observed pixels are 0 there and −1 here. Needs `xarray` and `rioxarray`; skipped without them.
- `test_matches_archive.py`: the copies in `snow/` give identical output to the originals in `../archive/`.
- `test_pca.py`: PC1 recovers the synthetic true pattern (r > 0.99) with covariance and correlation PCA; sign rule.
- `test_watershed.py`: South Fork Boise mask = 15,741 pixels (center rule) / 16,422 (all touched), area within 1% of WBD, one tile (h09v04).
- `test_tui.py`: three additional workbench tests cover threshold-dependent dates,
  GeoTIFF masks/readback, CSV pixel counts, single/multiple-year behavior,
  inside/outside map clicks across all projections, GUI threshold recalculation,
  invalid inputs, and calculation progress. These three tests passed locally
  on October 27, 2026; the complete pytest suite was not rerun for this addition.

## Jobs

### Interactive terminal workbench

#### Setup and launch

Windows: double-click `Snow-Workbench.cmd` in the repository root. It uses
`api/.venv`, then the existing local `demo/.venv`, then `python`.
Alternatively, from `api/` with `requirements.txt` installed, run:

```
python -m jobs.tui
```

For an explicit environment without activation, from `api/` use
`.venv\Scripts\python -m jobs.tui` on Windows or
`.venv/bin/python -m jobs.tui` on macOS/Linux. Python 3.12 is the documented
baseline. Install `requirements.txt` first, including numpy, rasterio, pyhdf,
earthaccess and matplotlib. The GUI additionally needs a desktop session and
an interactive matplotlib backend; the current Windows environment uses TkAgg.
No Earthdata login or network access is needed for synthetic mode.

The launcher keeps its window open on exit or failure so errors remain visible.
Its `demo/.venv` fallback is a legacy local environment, not a directory that
new users need to create. Prefer the documented `api/.venv` setup.

#### Menu and first run

| Key | Action |
|---|---|
| 1 | Edit settings. Enter keeps each current value; changes take effect on the next run. |
| 2 | Toggle synthetic demo / real MODIS. Downloading alone does not change mode. |
| 3 | Check local daily file coverage for the selected years and watershed, regardless of mode. |
| 4 | Download real daily files after typing `download` to confirm; no calculation is performed. |
| 5 | Calculate annual per-pixel FDL/LDS, optional multiyear PCA, and export a new run. |
| 6 | Open the most recent result in the clickable watershed pixel explorer. Run option 5 first. |
| 7 | Inspect the most recent result by zero-based row,column in the terminal. |
| q | Exit. In the text pixel inspector, q returns to the menu. Close the map window to return. |

For practice, keep the initial settings and choose **5**, then **6**. For real
data, use **1** to choose years/settings, **2** to select REAL MODIS, **4** to
download, **3** to check coverage, and **5** to process. Earthdata login setup
is described below and in [the access guide](../get_EarthData_Access.md).

#### Settings and scientific meaning

| Setting | Default | Meaning |
|---|---|---|
| Years | 2020, 2021, 2022 | Accepts single years, comma/space lists and inclusive ranges, such as `2020-2022,2024`. Allowed from 2000 through the current year; availability is checked separately. One year produces FDL/LDS only; PCA requires at least two. |
| NDSI threshold | 10 | Snow when NDSI >= threshold; readings below are snow-free. Cloud/night/fill flags remain unknown. Fractional thresholds are supported; range is greater than 0 through 100. |
| Search anchor DOY | 91 | Starting point for forward/backward melt search, not the first input day. DOY 91 is April 1 in a non-leap year, March 31 in a leap year. |
| Last observation DOY | 243 | Read January 1 through this day. DOY 243 is August 31 in a non-leap year, August 30 in a leap year. Current workbench limit is 365; must be at least the anchor. |
| Watershed | South Fork Boise, HUC8 17050113 | WGS84 lon/lat GeoJSON. Pixel centers define inclusion; multi-feature files combine their geometries. Must fit within one MODIS tile. |
| PCA scaling | covariance | Centers years without equalizing spread. `correlation` also rescales each year. Both remain available pending decision D06. |

An early observation cutoff can miss later melt. In particular, setting anchor
and cutoff both to 110 does not request a day-110 snow map: it truncates the
season at day 110. Code 365 then means **no melt found by the cutoff**, not proof
that snow lasted the whole calendar year. Returning snow is ignored by the
existing FDL method. The current implementation also uses code 365 in leap years.

Changing the NDSI threshold requires processing daily observations again;
threshold-10 FDL rasters cannot supply threshold-40 dates. The workbench uses
daily files directly rather than the precomputed `fdl_store/`.

#### Data, outputs and map controls

The numbered menu starts in **synthetic demo** mode: artificial daily NDSI on
the real South Fork Boise grid, for experimentation only. Settings include
years (`2020-2022,2024`), NDSI threshold (default 10), search start/end DOY,
WGS84 watershed GeoJSON, and covariance/correlation PCA (D06 remains open).
Switch to real MODIS to use local daily files. Download real data is a separate
confirmed action using the existing Earthdata login; it retains files in
`db/raw/` for reuse at other thresholds (about 0.55 GB per tile-year).
Real processing requires every day from DOY 1 through the chosen end day
(default 243); missing or duplicate dates are rejected. This first version
supports MODIS and single-tile watersheds only.

Each Run + export recalculates FDL/LDS at the selected threshold and creates a
separate `output/tui/` folder: annual FDL/LDS GeoTIFFs, `settings.json` provenance,
and `pixels.csv` for all watershed pixels with native-grid coordinates and
annual FDL/LDS/PC1 values. Outside the boundary is nodata. Codes: -1 unknown,
0 never snow, 365 never melted. One year returns FDL/LDS only; multiple years
also return PC1 when sufficient valid, varying observations exist. Higher PC1
means later relative melt, not a date or snow volume. Option 6 opens a clickable
watershed map: select an FDL year or PC1 layer, then click an inside pixel to
see annual FDL/LDS dates and PC1. Gray is outside the watershed; pale green
marks inside cells without valid melt dates. The toolbar supports zoom/pan;
disable zoom/pan before selecting. Close the map to return to the terminal.
The projection selector offers pixel grid, native MODIS sinusoidal, longitude/
latitude (WGS84), Web Mercator, and the watershed's local UTM zone. Only display
cell corners are transformed; scientific raster values and exports stay on the
original MODIS grid. Clicks transform back to the original cell before lookup.
Change the NDSI threshold in the map's top input box and click **Apply +
recalculate** to recompute annual FDL/LDS and PC1 from the same daily inputs.
This retains the run's watershed, years, mode, search days and PCA scaling,
refreshes the map and selected pixel, and saves a separate output folder.
Real inputs must still be available locally; this action does not download data.
The map may pause during processing. Closing it returns the updated result to
the terminal inspector; terminal Settings remain independently editable.
Calculation progress appears as a percentage bar in the terminal and map window,
with the active phase (daily reads, FDL/LDS, PCA, exports). Percentages measure
completed work across phases, not estimated elapsed time. Long individual PCA
operations retain their current phase percentage until finished. Downloads show
completed-file progress in batches of up to eight files; existing files are skipped.
This desktop window requires an interactive matplotlib backend (TkAgg works
with the existing Windows environment). Option 7 retains text inspection by
zero-based row,column (blank selects an inside pixel). Processing is synchronous;
Ctrl+C cancels to the menu. Restart the workbench after code updates.

Workbench checks: `python -m unittest discover -s tests -p test_tui.py`.

Each successful run writes `api/output/tui/<UTC timestamp>/` (gitignored):

| File | Contents |
|---|---|
| `fdl_<year>.tif` | int16 first-day-land DOY for each watershed pixel. |
| `lds_<year>.tif` | int16 last-day-snow DOY from the same search. |
| `pc1.tif` | Recurring relative melt scores; omitted for one year or unavailable PCA. |
| `pixels.csv` | One row per inside pixel: zero-based row/col, native-grid center x/y in meters, PC1, then FDL/LDS columns per year. Unavailable PC1 is blank. |
| `settings.json` | Actual run settings, synthetic/real source, product/layer, tile, CRS/transform/shape, boundary hash, processing identifier, masks/conventions, QA policy and real input filenames. Keep this alongside the rasters. |

Annual rasters retain special values; PCA excludes any pixel with unknown,
never-snow or never-melted FDL in any selected year. Exports retain the original
MODIS grid, with outside cells marked nodata. `settings.json` is a run manifest,
not complete historical provenance: it does not hash raw daily files or pin all
runtime/library versions. A failed/cancelled run can leave partial outputs;
only a reported successful completion establishes that all exports finished.

The grid rectangle contains cells outside the irregular watershed. The default
155 x 324 South Fork Boise grid therefore does not make every row/column pair
selectable. The map highlights the selected cell and shows annual calendar dates
in a side panel; long year lists continue in the terminal. The initial inside
pixel is selected automatically. The PC1 layer may be empty for a single year.
Map projection/layer changes affect display only and do not recalculate dates.

#### Troubleshooting and limits

| Symptom | What to do |
|---|---|
| Double-click does nothing / missing module error | Run the launcher from a terminal to read the error, or use the explicit environment command above. Install `requirements.txt` into that same environment. |
| Old menu or controls after an update | Exit and restart the workbench; already-open Python sessions keep old code. |
| No desktop map / noninteractive backend | Use a desktop Python environment with matplotlib and Tk support. If available, select `MPLBACKEND=TkAgg` before launch. Text inspection is option 7. |
| Click does not select | Turn off toolbar Zoom/Pan, then click inside the watershed. Gray outside cells cannot be selected. |
| FDL/LDS absent for some cells | Check special codes, threshold, season cutoff and actual observations; missing data is not land. |
| PC1 unavailable | Use multiple years with enough common valid pixels and spatial variation. Inspect FDL/LDS even when PCA is unavailable. |
| Real processing reports missing / duplicate days | Download missing daily files or retain one product version per date in the configured raw folder. Do not silently substitute a partial season. |
| GUI Apply fails | Read the terminal error. Existing results remain displayed. Real daily files must still exist locally. |
| Percentage pauses | A phase such as PCA may be one blocking operation. Progress measures work, not seconds; GUI processing is synchronous. Downloads update after batches finish. |

VIIRS, multi-tile stitching, a basemap, persistent settings/reopening saved runs,
background processing and cloud-gap filling are not implemented in this
workbench. Settings/results are held in memory until exit; exported files remain.
Progress bars described here belong to this workbench and its download action;
other standalone jobs retain their own reporting. No download integrity or
production-readiness claim is established by the synthetic workbench tests.

### Other jobs

**Team FDL vs. Woodruff FDL:** `python -m jobs.compare_woodruff_fdl --years 2000-2016 --download --delete-raw` (needs `requirements-validation.txt` and Woodruff's reference files in `db/validation/woodruff/source/`, either his original ZIP as `Collect-WoodruffValidation.ps1` stores it or the unzipped `FDL_NDSI10/` and `Watershed_boundary/`; `--reference` takes a ZIP or folder elsewhere). Computes FDL from the daily files four ways, compares each with Woodruff's mosaic pixel by pixel, then runs the same PCA on team and Woodruff FDLs. Without `--download`, the daily files must already be in `db/raw/`. Result (2026-10-20, 2000–2016): the current method matches exactly on 97.9% of pixel-years (90.2–99.6% by year), and PC1 from team FDLs correlates 0.9998 with PC1 from Woodruff's. See `Admin_And_Docs/Planning/woodruff-fdl-comparison-2026-10-20.md`.

**Woodruff reference-input validation:** install the optional
`requirements-validation.txt` dependencies, then run
`python -m jobs.validate_woodruff --archive PATH_TO_ZIP`.
This reads the supplied FDLs and boundary directly from the ZIP, checks grid
alignment, compares covariance/correlation PCA and verifies covariance against
independent SVD. It writes GeoTIFFs and statistics under
`output/woodruff_validation/`. See the
[October 13 validation report](../Admin_And_Docs/Planning/woodruff-validation-2026-10-13.md)
for results and remaining reference comparisons.

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

**Download raw files** (used by `run_real.py`, comparison jobs and the workbench): `python -m jobs.download --years 2020 2021 --tile h09v04`. Files go to `db/raw/` (gitignored; deleting them requires downloading again for recalculation).

**End-to-end check:** `python -m jobs.run_real --years 2020 2021 2022 2023 2024`. Defaults to South Fork Boise (HUC8 17050113) from `db/boundaries/`. Options: `--geojson`, `--threshold`, `--start-doy`, `--correlation`. Writes to `api/output/` (gitignored). Refuses watersheds spanning two tiles.

## `snow/fdl.py` vs. the starter code

Same algorithm as `../reference/Starter_Code_FDL_LDS_MOD10A1F.py` (start on DOY 91; search forward for pixels that are snow that day, backward for pixels that are clear; returning snow ignored). Changes:
- Reads `CGF_NDSI_Snow_Cover` by name as raw uint8 with `pyhdf`, so fill and missing codes stay codes instead of becoming NaN (which gave FDL = 0).
- Raises if the HDF grid metadata can't be parsed, instead of falling back to the h00v00 origin.
- Pixels never observed as snow or clear get −1 (no data), kept apart from 0 (never snow) and 365 (never melted).

Not changed: the start-day FDL for pixels missing on DOY 91 (ask Woodruff), 365 in leap years, ocean = 0, and LDS ignoring `Cloud_Persistence`.

## Conventions

PCA is covariance by default with `use_correlation=True` available (D06 open); scores are the uncentered projection; the sign is flipped so higher PC1 = later melt; pixels with 0, 365 or −1 in any year are dropped before PCA. Details in [`../CLAUDE.md`](../CLAUDE.md) and the [decision register](../Admin_And_Docs/Planning/decisions.md).

History: the first real-data results (South Fork Boise 2020–2024), timings and the data-access findings are in [`../archive/realdata/README.md`](../archive/realdata/README.md).
