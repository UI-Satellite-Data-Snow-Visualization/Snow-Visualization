# Team FDL vs. Woodruff FDL, 2000–2016

Run October 20, 2026. Independent check of the team's FDL step, and of the full FDL → PCA pipeline, against Woodruff's reference rasters. The team computed FDL from NASA's daily files for all 17 years and compared it pixel by pixel with his, then ran the same PCA on both. This complements `woodruff-validation-2026-10-13.md`, which checked PCA on Woodruff's own FDLs.

## Inputs

- **Reference:** `FDL_NDSI10/MOSAIC/FDL<year>_m.tif` (2000–2016) and `Watershed_boundary/` from Woodruff's archive (the files Tyler inspected on October 13; re-running `jobs.validate_woodruff` on this copy reproduced all 269 values in `woodruff-validation-2026-10-13-results.json`). Each mosaic is 2400 × 4800 uint16, MODIS sinusoidal, 463.3127 m, upper-left corner at tile h09v04's corner: h09v04 and h10v04 side by side on the native grid, so no resampling is needed. All 17 mosaics carry an ArcGIS creation date of 2021-04-20.
- **Team input:** MOD10A1F v61, h09v04 and h10v04, DOY 1–243 each year (2000 starts at DOY 55, when Terra data begins), downloaded from NSIDC on 2026-10-20. About 0.55 GB per tile-year; each year's files were deleted after comparison (`--delete-raw`).
- **Mask:** all 764 boundary features, reprojected onto the mosaic grid, pixel center inside: 41,346 pixels (17,001 in h09v04, 24,345 in h10v04).
- **Code:** `api/jobs/compare_woodruff_fdl.py`, using `snow/fdl.py`, `snow/matrix.py` and `snow/pca.py` unchanged, NDSI ≥ 10.

Four FDL variants were computed from the same files, because the history behind Woodruff's rasters is unconfirmed: **A** gap-filled `CGF_NDSI_Snow_Cover`, DOY 91 two-way search (the current starter script and `snow/fdl.py`); **B** cloud-containing `MOD10A1_NDSI_Snow_Cover`, DOY 91 two-way; **C** cloud-containing, forward from DOY 1; **D** gap-filled, forward from DOY 1.

## FDL results

Melt-date agreement is measured on pixels where both have a date (1–364). "Code class" compares the special values: 0 never snow, 365/366 never melted, a date, or no data.

| Year | A exact | A within 3 d | A mean diff (d) | A code class agrees | B exact | C exact |
|---|---|---|---|---|---|---|
| 2000 | 97.8% | 99.0% | +0.0 | 99.99% | 97.1% | 97.9% |
| 2001 | 97.8% | 98.8% | +0.1 | 100% | 95.2% | 98.0% |
| 2002 | 98.6% | 99.2% | +0.1 | 100% | 97.0% | 98.1% |
| 2003 | 99.2% | 99.6% | +0.0 | 100% | 94.1% | 96.4% |
| 2004 | 97.3% | 98.2% | +0.2 | 100% | 94.0% | 99.3% |
| 2005 | 99.6% | 99.7% | −0.0 | 100% | 97.9% | 98.3% |
| 2006 | 99.2% | 99.6% | +0.0 | 100% | 98.7% | 98.7% |
| 2007 | 97.4% | 97.8% | +0.3 | 100% | 92.5% | 99.4% |
| 2008 | 99.2% | 99.7% | +0.0 | 100% | 99.2% | 99.1% |
| 2009 | 99.5% | 99.7% | +0.0 | 100% | 99.3% | 99.2% |
| 2010 | 97.8% | 97.9% | −0.5 | 100% | 98.2% | 96.5% |
| 2011 | 99.4% | 99.8% | −0.0 | 99.99% | 97.3% | 99.2% |
| 2012 | 98.6% | 99.1% | +0.1 | 100% | 96.8% | 98.6% |
| **2013** | **90.2%** | **94.0%** | −0.4 | 100% | 88.4% | 90.0% |
| 2014 | 98.2% | 99.3% | −0.0 | 100% | 97.6% | 98.0% |
| 2015 | 95.3% | 97.1% | +0.2 | 100% | 91.1% | 94.3% |
| 2016 | 98.9% | 99.5% | +0.0 | 100% | 97.3% | 97.7% |
| **All years (pooled)** | **97.9%** | | | | 96.0% | 97.6% |

D equals C on every pixel (pooled 97.6%): the gap-filled layer repeats the last real observation, so a forward search finds the same first clear day in both layers.

- **Variant A matches best overall** (97.9% of pixel-years exactly). In 15 of 17 years it matches 97.3–99.6% exactly, and the median difference is 0 days in every year. C is higher in 2004 and 2007 (and by 0.1 point in 2000), and B in 2010.
- **Special codes agree almost everywhere.** Never-snow and never-melted pixels are essentially absent inside this boundary; code-class agreement is 100% in 14 years and at least 99.99% in the rest.
- **Two weaker years: 2013 (90.2%) and 2015 (95.3%).** Their mismatches sit near the DOY 91 start. In 2013, most are pixels both place after April 1 but the team places earlier, most often team DOY 92 vs. Woodruff DOY 100–113; mismatches cluster in the low, early-melting valleys of the southwest. In 2015, 564 pixels are clear before April 1 in Woodruff's raster (DOY 86–89) but melt after it in the team's (DOY 93–103). 2007 and 2010 show smaller near-start disagreements in opposite directions.

## PCA on team FDL vs. PCA on Woodruff FDL

Same pixels for both (41,336: a date in every year in both datasets; 10 pixels dropped), same code (`snow/pca.py`).

| PCA | PC1 variance, team | PC1 variance, Woodruff | PC1 Pearson r | PC1 Spearman | Max year-weight difference |
|---|---|---|---|---|---|
| Covariance | 93.65% | 93.60% | 0.9998 | 0.9998 | 0.0072 |
| Correlation | 93.75% | 93.68% | 0.9998 | 0.9998 | 0.0012 |

- PC1 values (covariance) span about 394–765 (2nd–98th percentile). Team minus Woodruff: median absolute difference 0.14; 95% of pixels within 3.3; 99% within 9.2; maximum 38. 4.3% of pixels differ by more than 1% of that span. Differences appear as scattered pixels and short streaks, mostly where 2013 disagreed (`pca_compare.png`).
- So the FDL differences above barely change the recurring melt pattern the tool would show.

## What NASA's file dates show

NASA's current MOD10A1F v61 files were produced year by year from early 2020 to late 2021. Production dates (h10v04, Jan–Aug files): 2000–2006 in 2020; 2007 and 2008 before 2021-04-20; **2009–2016 from May to December 2021**, after the date on Woodruff's mosaics. So his 2009–2016 FDLs can't have been made from the files downloaded here; he must have used an earlier version of the data (likely the previous collection, unconfirmed). However, agreement doesn't track file age: 2009, 2011 and 2016 (newer files) match at 98.9–99.6%, while 2004 and 2007 (files produced before his mosaics) match at about 97.3%. The cause of the year-to-year differences is not established. Candidates: different input files or versions, or a processing difference near the start date. Only Woodruff can settle it.

## Why 2013 is lower

Investigated by re-downloading 2013 and inspecting the daily observations of the 4,061 mismatched pixels (a throwaway script, not in the repo).

- **Not the start date.** Rerunning the team FDL with start dates from DOY 70 to 120 never exceeds 93.0% exact (best: DOY 112). No single start date reproduces Woodruff's 2013.
- **The team's dates are real clear observations.** On the team's FDL day, 3,993 of the mismatched pixels (98%) were actually observed clear in the cloud-containing layer (`Cloud_Persistence` 0, so not gap-filled), with NDSI 0, the same value as matching pixels. They aren't borderline readings near the threshold of 10.
- **Woodruff's dates often aren't clear in today's data.** On his FDL day, today's files show snow for 1,053 of these pixels and cloud for 295.
- **The pattern is a brief clear spell followed by more snow.** Most mismatched pixels are seen clear on one clear day near April 1 (DOY 90 and 92 were 98% cloud-free across the watershed), then snow again in April (1,877 have one or more real snow observations between the two FDLs). The method takes the first clear day after the start and ignores returning snow, as designed. Woodruff's dates fall later.

Conclusion: in 2013, Woodruff's FDLs are inconsistent with today's MOD10A1F observations under the same algorithm: some of his dates fall on days today's data shows as snow-covered. The most likely explanation is that his 2013 input data differed. Today's 2013 files were produced in August 2021, after his mosaics, so he must have used an earlier version. That is likely but unconfirmed: it requires his input files or his answer. A spring with a brief clear spell and then more snow near the start date is exactly where any difference in the daily data changes FDL most, which would explain why 2013 is affected more than other years.

## What this shows and doesn't show

- **Shows:** the team's FDL implementation reproduces Woodruff's FDLs closely across 17 years of real data (97.9% exact overall), and the full pipeline from daily files to PC1 reproduces the PC1 his FDLs give (r = 0.9998). Overall, the current method (gap-filled layer, DOY 91 two-way search) fits his rasters better than the alternatives tested.
- **Doesn't show:** agreement with Woodruff's own PC1 (none supplied), which PCA scaling is correct (D06; the two scalings also agree closely here), or LDS (not compared). Exact reproduction isn't possible without knowing his input files.
- **To ask Woodruff:** which collection/version of MOD10A1F the 2000–2016 FDLs used and when they were computed; whether his 2013 data showed the early-April clear days (DOY 90 and 92) as clear; and whether the start date or processing differed in 2013 and 2015.

## Reproduce

From `api/`, with Woodruff's files in `db/validation/woodruff/source/` (gitignored), either his original ZIP or unzipped `FDL_NDSI10/` and `Watershed_boundary/`; `--reference` takes a ZIP or folder elsewhere:
```
.venv/bin/python -m jobs.compare_woodruff_fdl --years 2000-2016 --download --delete-raw
```
About 30 minutes, almost all downloading (~17.6 GB fetched, at most about 1 GB on disk at once); each year's comparison takes seconds. Writes per-year `compare_<year>.json`, `diff_<year>.png` and `team_fdl_<year>.tif`, plus `summary.json`, `pca_compare.json` and `pca_compare.png`, to `api/output/woodruff_fdl/` (gitignored). macOS, Python 3.12, numpy 2.5, rasterio 1.5, pyhdf, earthaccess 0.19.
