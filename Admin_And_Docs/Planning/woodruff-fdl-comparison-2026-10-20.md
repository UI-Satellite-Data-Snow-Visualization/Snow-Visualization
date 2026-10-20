# Team FDL vs. Woodruff FDL (2016)

Run October 20, 2026. First independent check of the team's FDL step against Woodruff's reference rasters: the team computed FDL from NASA's daily files and compared it pixel by pixel with his. This complements `woodruff-validation-2026-10-13.md`, which checked PCA on Woodruff's own FDLs.

## Inputs

- **Reference:** `FDL_NDSI10/MOSAIC/FDL2016_m.tif` and `Watershed_boundary/` from Woodruff's archive (the same files Tyler inspected on October 13; re-running `jobs.validate_woodruff` on this copy reproduced all 269 values in `woodruff-validation-2026-10-13-results.json`). The mosaic is 2400 × 4800 uint16, MODIS sinusoidal, 463.3127 m, upper-left corner at tile h09v04's corner: h09v04 and h10v04 side by side on the native grid, so no resampling is needed.
- **Team input:** MOD10A1F v61, h09v04 and h10v04, 2016 DOY 1–243 (243 files per tile), downloaded with `jobs.download` to `db/raw/`.
- **Mask:** all 764 boundary features, reprojected from the shapefile's projection onto the mosaic grid, pixel center inside: 41,346 pixels (17,001 in h09v04, 24,345 in h10v04). Same count as the October 13 report.
- **Code:** `api/jobs/compare_woodruff_fdl.py`, using `snow/fdl.py` unchanged, NDSI ≥ 10.

## Results

Four variants were computed from the same files, because the history behind Woodruff's rasters is unconfirmed. Compared on pixels where both have a melt date (1–364); none of the 41,346 pixels had 0, 365 or 366 in any variant or in the reference.

| Variant | Layer | Start | Exact match | Within 3 days | Within 7 days | Mean difference | Pearson r |
|---|---|---|---|---|---|---|---|
| **A (current starter script)** | `CGF_NDSI_Snow_Cover` | DOY 91, two-way | **98.9%** | 99.5% | 99.8% | +0.0 days | 1.000 |
| B | `MOD10A1_NDSI_Snow_Cover` (cloudy) | DOY 91, two-way | 97.3% | 98.7% | 99.6% | −0.1 days | 0.999 |
| C | cloudy | DOY 1, forward | 97.7% | 98.3% | 98.6% | −0.5 days | 0.970 |
| D | gap-filled | DOY 1, forward | 97.7% | 98.3% | 98.6% | −0.5 days | 0.970 |

- **The current method reproduces Woodruff's 2016 FDL.** Variant A matches exactly on 98.9% of pixels with no bias. The remaining 1.1% are scattered single pixels, mostly 1–5 days off, with no spatial pattern, tile seam or dependence on melt date (`api/output/woodruff_fdl/diff_2016.png`).
- **C and D are identical on every pixel, as expected.** The gap-filled layer repeats the last real observation, so in a forward search it stays "snow" until the first clear sighting of land, the same day the cloudy layer first shows land. The two layers differ only in the backward search (A vs. B).
- **Clumped FDL dates don't indicate the cloudy layer.** The reference's FDLs cluster on a few days (e.g. DOY 122 and 149 hold over 3,000 pixels each). Variant A clusters the same way, because gap-filling also holds snow until the next clear day.

## What this does and doesn't show

- It supports the team's FDL implementation (`snow/fdl.py`, task 2.5) on real daily data for one year, against the author's own output. It suggests the reference rasters were made with the current MOD10A1F/DOY 91 method, or one that gives nearly the same result; that still needs Woodruff's confirmation.
- Cause of the 1.1% residual not established. Candidates: a different download of MOD10A1F (NASA reprocesses files; the reference mosaic was made in April 2021), or small differences between his processing and the starter script. Not caused by the team's fixes: those only change never-observed pixels, and there were none.
- One year only (2016, a leap year). The script takes `--year`; repeating for more years needs about 1.1 GB of downloads per year.
- LDS not compared.

## Reproduce

From `api/`, with Woodruff's files in `db/validation/woodruff/source/` (gitignored), either his original ZIP or unzipped `FDL_NDSI10/` and `Watershed_boundary/`; `--reference` takes a ZIP or folder elsewhere:
```
.venv/bin/python -m jobs.download --years 2016 --tile h09v04
.venv/bin/python -m jobs.download --years 2016 --tile h10v04
.venv/bin/python -m jobs.compare_woodruff_fdl --year 2016
```
Downloads took a few minutes; the comparison about 5 seconds. Writes `api/output/woodruff_fdl/compare_2016.json` and `diff_2016.png` (gitignored). macOS, Python 3.12, numpy 2.5, rasterio 1.5, pyhdf.
