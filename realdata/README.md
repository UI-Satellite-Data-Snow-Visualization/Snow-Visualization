# Real-data pipeline (MOD10A1F → FDL → PCA)

First end-to-end run on real NSIDC data: daily MOD10A1F in, a PC1 map and GeoTIFF out, for one watershed. It reuses `demo/snowpca` for the watershed mask, D matrix and PCA, and the venv in `demo/`.

## Setup and download

**1. Python environment.** Uses the venv in `demo/`:
```
cd demo
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r ../realdata/requirements.txt
```

**2. Earthdata login** (free account at https://urs.earthdata.nasa.gov/). `download.py` tries these in order and never prompts:
- `EARTHDATA_TOKEN` environment variable, as in `get_EarthData_Access.md` (on macOS/Linux: `export EARTHDATA_TOKEN=...`), or `EARTHDATA_USERNAME` + `EARTHDATA_PASSWORD`.
- `~/.netrc` with a `urs.earthdata.nasa.gov` entry. To create one, run once: `demo/.venv/bin/python -c "import earthaccess; earthaccess.login(persist=True)"` (asks for username and password).

If neither is set, it exits with a message saying so. **For Claude sessions:** the person sets up the login themselves, e.g. by typing `! <command>` in Claude Code. Never ask for, read or write the token, password or `~/.netrc` contents.

**3. Download.**
```
cd realdata
../demo/.venv/bin/python download.py --years 2020 2021 2022 2023 2024
```
- Fetches MOD10A1F v61, DOY 1–243 (Jan 1–Aug 31), one tile (`--tile`, default h09v04; Idaho also needs h10v04). Other options: `--last-doy`, `--out`.
- Size and time: 243 files, about 0.55 GB, about 40 s per tile-year at the ~13 MB/s measured here. Five years took a few minutes. Run long downloads in the background.
- Safe to re-run: files already in `downloads/` are skipped, so an interrupted download resumes.
- Check: each year should have 243 files, e.g. `ls downloads | grep -c A2024` → 243.
- `downloads/` and `output/` are gitignored. Never commit the HDF files.

**4. Run the pipeline.**
```
../demo/.venv/bin/python run_real.py --years 2020 2021 2022 2023 2024
```
- Defaults to South Fork Boise (HUC8 17050113). Options: `--geojson`, `--threshold` (default 10), `--start-doy` (default 91), `--correlation` (correlation PCA instead of covariance; D06 is open). It overwrites `output/`, so a `--correlation` run replaces the covariance outputs.
- Watersheds that span more than one tile are refused until tile stitching exists.

Outputs in `output/`: `fdl_<huc>_<year>.tif` (int16, MODIS sinusoidal; 0 = never snow, 365 = never melted, −1 = no data), `pc1_<huc>.tif` (float32, NaN outside the watershed) and `real_pc1.png`. The figure shows the PC1 map (dark = earlier, light = later; relative, not dates), a bar chart of variance explained per component, and one FDL map per year on a shared date scale with each year's median. Maps are reprojected to Web Mercator (nearest neighbor) for display only.

## `fdl.py` vs. `Starter_Code_FDL_LDS_MOD10A1F.py`

Same algorithm as Woodruff's starter code (anchor on DOY 91, forward search for pixels that are snow that day, backward for pixels that are clear). The original is untouched. Changes, from the known problems listed in `CLAUDE.md`:
- Reads `CGF_NDSI_Snow_Cover` by name, as raw uint8, with `pyhdf`. Fill and missing codes stay codes instead of becoming NaN.
- Reads only the watershed's window of the tile, not all 2400 × 2400 pixels.
- Raises if the HDF grid metadata can't be parsed, instead of falling back to the h00v00 origin.
- Pixels never observed as snow or clear get −1, kept apart from 0 and 365.

Not changed: the start-day FDL for pixels missing on DOY 91 (problem 3; ask Woodruff), 365 in leap years, ocean = 0, and LDS ignoring `Cloud_Persistence`.

**Equivalence check (2026-10-06).** Both scripts were run on 199 synthetic daily HDF4 files (30 × 40 pixels, with cloud, missing, inland water, ocean, returning snow, never-melted and never-snow pixels). FDL and LDS matched on every pixel, except 5 never-observed pixels, where the original gives 0 and `fdl.py` gives −1.

## Results (2026-10-06, South Fork Boise, 2020–2024, NDSI ≥ 10)

| Year | Median FDL (DOY) | 10–90% of pixels |
|---|---|---|
| 2020 | 105 | 71–148 |
| 2021 | 102 | 80–137 |
| 2022 | 92 | 77–158 |
| 2023 | 131 | 105–158 |
| 2024 | 106 | 79–140 |

- All 15,741 masked pixels had a real FDL every year (no 0, 365 or −1), so D is 15,741 × 5.
- Covariance PCA: PC1 93.1%, PC2 4.1%; year weights 0.37–0.56; year correlations with PC1 0.93–0.98 (weakest 2023, a late-melt year). Correlation PCA (`--correlation`): PC1 93.3%, weights 0.44–0.46.
- **2022 shows the start-date effect.** A warm March left 47% of the watershed bare on April 1 (4–28% in other years), and April storms brought snow back. 6.1% of the watershed was bare on April 1 and then had at least 10 April snow days (≤ 0.1% in other years). Those pixels search backward and get March FDLs; neighbors still snowy on April 1 search forward through the storms and get June FDLs. That leaves a sharp edge along the April 1 snow line in the 2022 map. The method is working as designed (returning snow is ignored), but it supports Woodruff's point that the start date is the critical setting, and it's a test case for automatic start-date detection. Not checked: whether MOD10A1F's gap filling makes that edge look straighter than the real snow line.
- The PC1 map is earliest in the low western end and river valleys and latest on the high northeastern ground. This is a plausibility check only; nothing has been compared against Woodruff's reference rasters yet.

## Timing (measured 2026-10-06, 14-core Mac, 38 GB RAM)

| Step | Time |
|---|---|
| Watershed run, 5 years (windowed read + FDL + PCA) | ~2 s |
| Read one full tile-year (243 files, 2400 × 2400) | 1.7 s (files probably still in OS cache) |
| FDL on one full tile-year | 5.0 s, peak RAM 6.6 GB |
| Mask and crop a stored tile FDL to the watershed | 13 ms; matched the windowed run on every pixel |
| Download | ~13 MB/s; ~0.55 GB per tile-year |

**Idaho estimate.** The state outline fits in two tiles, h09v04 and h10v04 (checked by projecting points along Idaho's bounding box). 25 years (2000–2024) = 50 tile-years: about 27 GB and ~35 min to download, ~6 min of FDL (1–2 min running 4–5 tile-years in parallel). Watersheds that cross the state line likely add the v05 tiles (NV/UT) and v03 tiles (Canada), so 4–6 tiles; not checked against the real HUC8 list. 2000 starts on Feb 24, so its backward search has less winter.

## Data access: download vs. API (checked 2026-10-06)

- **MOD10A1F** (NASA CMR, collection `C3028765772-NSIDC_CPRD`): offered only as whole files, over HTTPS or direct S3 in `us-west-2` (`nsidc-cumulus-prod-protected/MODIS/MOD10A1F/61`). No subsetting service is registered, and AppEEARS doesn't carry it. HDF4 can't be read in parts remotely, so each daily file is fetched whole.
- **AppEEARS** does carry MOD10A1.061, MYD10A1.061, VNP10A1.002 and VJ110A1.002, clipped to a polygon. It is an asynchronous job queue (minutes to hours), so it suits batch precompute (cloud removal, VIIRS), not live requests.
- **Implication:** download each tile-year, compute FDL, delete the raw files, keep only the int16 FDL rasters (about 11 MB per tile-year uncompressed; ~0.5 GB for 25 years × 2 tiles vs. ~27 GB raw). User requests then only crop and run PCA. Running on AWS `us-west-2` could read straight from S3 with `earthaccess.open()`; on UI RCDS hosting, HTTPS download is the realistic path.

## Data and processing record

| Item | Value |
|---|---|
| Product | MOD10A1F, collection 6.1 (v61), NSIDC, via `earthaccess` |
| Layer | `CGF_NDSI_Snow_Cover` (uint8). The file has no elevation layer; its layers are `CGF_NDSI_Snow_Cover`, `Cloud_Persistence`, `Basic_QA`, `Algorithm_Flags_QA`, `MOD10A1_NDSI_Snow_Cover` |
| Tile, dates | h09v04, DOY 1–243 |
| Threshold | Snow = NDSI 10–100; clear = NDSI < 10 or 237; missing = 200, 201, 211, 250, 254, 255 |
| CRS, grid | `+proj=sinu +R=6371007.181`, 463.31 m pixels, read from the file's `StructMetadata.0` |
| Boundary | `demo/data/wbd_huc8_17050113.geojson`, pixel center inside |
| PCA | Covariance (default), uncentered projection; pixels with 0, 365 or −1 in any year are dropped |
