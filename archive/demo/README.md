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

### Watershed masking (`watershed_demo.py`)

```
.venv/bin/python watershed_demo.py                  # South Fork Boise, HUC8 17050113
.venv/bin/python watershed_demo.py --all-touched    # count every pixel the boundary touches
.venv/bin/python watershed_demo.py --geojson path/to/boundary.geojson
```

This script uses a real USGS watershed boundary with synthetic FDL values inside it. It:
1. Reprojects the boundary (lon/lat) into the MODIS sinusoidal projection. The raster itself is never resampled.
2. Builds a grid lined up with the global MODIS 500 m pixel grid.
3. Converts the boundary into a pixel mask and runs the same PCA pipeline on the masked pixels.
4. Writes `output/pc1_<huc>.tif`, a GeoTIFF with nodata outside the watershed, then reads it back to confirm the CRS, transform and mask survived.
5. Saves `output/watershed_demo.png`. The left panel shows the mask on the native MODIS grid, which looks sheared because meridians lean about 54° at Idaho's longitude. The right panel shows PC1 reprojected to Web Mercator for display only, so the watershed looks as it does on web maps.

It needs `rasterio`. `run_demo.py` doesn't.

Results on 2026-09-29 for South Fork Boise:

| Measure | Result |
|---|---|
| Grid | 155 × 324 pixels |
| Mask (pixel center inside) | 15,741 pixels = 3,379 km² (WBD lists 3,384 km²) |
| Mask (`--all-touched`) | 16,422 pixels, about 4% more |
| MODIS tiles needed | h09v04 |
| Matrix | 15,539 pixels × 17 years |
| PC1 variance explained | 94.2% |
| PC1 vs. true synthetic pattern | r = 0.998 |
| Georeferencing check | Masked pixel centers convert back to lon/lat within half a pixel of the boundary's extent |

The measured area closely matches the WBD area because the sinusoidal projection preserves area.

**Boundary file:** `data/wbd_huc8_17050113.geojson`, 13 KB.
- Source: USGS Watershed Boundary Dataset, fetched on 2026-09-29 from `https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query?where=huc8='17050113'&outFields=huc8,name,areasqkm,states&outSR=4326&maxAllowableOffset=0.001&geometryPrecision=5&f=geojson`.
- The service simplified it to about 100 m, well below the 463 m pixel size.
- For another watershed, change the `huc8` value. Use layer 5 with `huc10` for HUC 10 watersheds, or layer 6 with `huc12` for HUC 12 subwatersheds.

Last run on 2026-09-29 (Python 3.12): PC1 explained about 94–95% of the variance and matched the true pattern with r ≈ 0.997–0.999. This is synthetic data, not evidence of real-world accuracy.

## Modules

| File | Purpose |
|---|---|
| `snowpca/dummy.py` | `make_dummy_fdl_stack()`: synthetic FDL rasters with year-to-year shifts, cloud delay, spurious early pixels, missing pixels and a watershed mask (a random blob, or a real one via `mask=`). Replace it with real NSIDC retrieval and FDL extraction later. |
| `snowpca/matrix.py` | `build_matrix()`: rasters → matrix plus a `PixelIndex` recording which pixels were kept. `to_raster()`: per-pixel values → grid. |
| `snowpca/pca.py` | `run_pca()`, `pc_as_doy()` and `summarize()`. |
| `snowpca/watershed.py` | MODIS 500 m grid constants and CRS, plus `load_boundary()`, `to_sinusoidal()`, `grid_for()`, `rasterize_mask()`, `modis_tiles()` and `write_geotiff()`. It is not imported by `snowpca/__init__.py`, so rasterio stays optional. |

## Conventions (decision D06)

- **Covariance PCA by default.** The default uses the covariance of the year columns and projects the raw values (the paper's equation 1). This matches scikit-learn's `PCA`, which Dr. Woodruff says they use: same PC1 eigenvector. `use_correlation=True` standardizes each year column. Dr. Qualls described that rescaling on 2026-10-01, so the choice is still open ([decisions.md](../Admin_And_Docs/Planning/decisions.md), D06). On the synthetic data the two give nearly the same melt order.
- **Sign rule.** The PCA sign is flipped so the year weights sum positive, which makes higher PC1 mean later melt.
- **Missing pixels.** Pixels valid in fewer than `min_valid_frac` of the years are dropped. The remaining gaps are filled with that pixel's mean across years. This is a placeholder until D05 is decided.
- **Watershed pixels.** A pixel is included if its center falls inside the boundary (GDAL's default). `--all-touched` is the alternative. Not yet decided (D08).

See `../Admin_And_Docs/Planning/pca-prototype-plan.md` and `decisions.md`.
