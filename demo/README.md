# PCA demo (synthetic data)

This demo is a prototype of the recurrent snowmelt pattern method from Woodruff & Qualls (2019), run on dummy data. Each year's first-day-land (FDL) raster is flattened into one column, giving a matrix with one row per pixel and one column per year. PCA runs on that matrix, and PC1 is mapped back onto the grid. No real satellite data is used.

## Run

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run_demo.py
```

The script runs three cases: 40×30 pixels × 8 years, 120×90 × 17 years (the paper's 17 years), and 250×200 × 25 years. For each case it prints:
- the variance explained,
- the range of PC1 weights,
- how strongly each year correlates with PC1,
- how many pixels were kept,
- how closely PC1 matches the known synthetic pattern.

It also saves `pc1_demo.png` next to the script, showing the true pattern, one noisy year, PC1 and a scree plot. Without matplotlib, the numbers still print and the figure is skipped.

Last run on 2026-09-29 (Python 3.12): PC1 explained about 94–95% of the variance and matched the true pattern with r ≈ 0.997–0.999. This is synthetic data, not evidence of real-world accuracy.

## Modules

| File | Purpose |
|---|---|
| `snowpca/dummy.py` | `make_dummy_fdl_stack()`: synthetic FDL rasters with year-to-year shifts, cloud delay, spurious early pixels, missing pixels and a watershed mask. Replace it with real NSIDC retrieval and FDL extraction later. |
| `snowpca/matrix.py` | `build_matrix()`: rasters → matrix plus a `PixelIndex` recording which pixels were kept. `to_raster()`: per-pixel values → grid. |
| `snowpca/pca.py` | `run_pca()`, `pc_as_doy()` and `summarize()`. |

## Conventions (provisional, decision D06)

- **Covariance PCA by default.** The default uses the covariance of the year columns and projects the raw values (the paper's equation 1). `use_correlation=True` standardizes each year column, as proposed in the planning docs.
- **Sign rule.** The PCA sign is flipped so the year weights sum positive, which makes higher PC1 mean later melt.
- **Missing pixels.** Pixels valid in fewer than `min_valid_frac` of the years are dropped. The remaining gaps are filled with that pixel's mean across years. This is a placeholder until D05 is decided.

See `../Admin_And_Docs/Planning/pca-prototype-plan.md` and `decisions.md`.
