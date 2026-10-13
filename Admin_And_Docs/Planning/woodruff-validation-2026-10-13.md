# Woodruff reference-input validation

Run and inspected October 13, 2026. This is completed validation evidence for the
PCA stage and a plan for the remaining reference comparisons. It does not replace
the project's complete Design Validation Plan.

## Source and provenance

The user supplied `OneDrive_1_10-13-2026.zip` from Downloads and identified it as
Woodruff's validation data. SHA256:
`f4bc57a456110f9790db2b1ddd20fdaf231cbdda87707291f51dcd8b30cb1480`.
The archive contains 17 FDL and 17 LDS mosaics (2000–2016), metadata and a
watershed shapefile. No reference PC1 raster or processing script is included.
The originals were read directly from the archive and left unchanged.

The folder name indicates NDSI 10. The 2000 XML records ArcGIS mosaicking on
April 20, 2021 of h09v04 and h10v04 inputs. This records a mosaic operation,
not the full FDL algorithm provenance. Product/collection, daily input dates,
search start/stop rules, QA policy, historical special-value meanings and
processing version still need confirmation. Do not assume these files were
produced by the current MOD10A1F v61 DOY-91 script.

## Method

Run `jobs.validate_woodruff` against the supplied archive. Check exact equality
of shape, CRS and transform across all 17 FDL rasters. Transform the supplied
boundary from NAD27 Albers onto the native MODIS sinusoidal grid; do not resample
the rasters. Rasterize all 764 supplied boundary features using pixel centers.
The raster mosaic is 2400 rows by 4800 columns at 463.3127165275 m resolution;
the boundary crop is 366 by 483.

Build a pixels-by-years matrix in raster row order with a common valid mask.
Conservatively exclude nonfinite values, declared nodata, values <=0 and >=365,
pending confirmation of historical codes. No interpolation or imputation.
Run the existing `snow.pca.run_pca` with covariance and correlation scaling,
projecting uncentered inputs and orienting weights to sum positive. Higher
scores indicate later relative melt timing, not exact dates or water volume.
Verify covariance weights and variance independently using centered-matrix SVD.
Write both PC1 GeoTIFFs and verify values, masks, CRS and transform by reopening.

## Results

| Check | Measured result | Interpretation |
| --- | --- | --- |
| FDL raster alignment | All 17 grids identical | Inputs can be stacked without resampling |
| Boundary mask | 41,346 pixels | All retained across all 17 years; D is 41,346 x 17 |
| Special codes inside boundary | No 0, 365 or 366 in any FDL year | Conservative exclusion has no effect in this boundary |
| Covariance PC1 variance | 93.604835% | Measured on these reference inputs |
| Correlation PC1 variance | 93.684388% | Similar concentration of variance |
| Covariance vs. correlation PC1 | Pearson 0.999860; Spearman 0.999903 | Very similar spatial timing patterns |
| Covariance year weights | 0.194013–0.307945 | Year contributions vary |
| Correlation year weights | 0.237664–0.245404 | More uniform year contributions |
| Covariance PC1/year correlation | 0.948661–0.979428 | Strong association across supplied years |
| Independent SVD check | Maximum weight difference 4.0e-15; variance difference 1.4e-15 | Agreement at floating-point precision |
| GeoTIFF readback | Both exports passed exact float32 value/mask and grid checks | Export preserves computed outputs and native geometry |

The supplied mask yields 157 fewer pixels than the 2019 paper's reported
41,503. Boundary version, rasterization and historical masking may explain
this; no explanation has been established. The measured variance differs from
the paper's 85%, but its threshold and processing differ from current direction.
Neither 85% nor the meeting's conflicting ~97% claim is an application target.
High variance alone does not establish scientifically correct melt dates.

## Conclusions and remaining validation

The repository PCA calculation is numerically consistent with an independent
SVD on Woodruff's real FDL inputs. Both available scaling options produce
similar patterns here. This does not resolve decision D06: no author PC1 raster
is available to select the matching convention. It also does not validate the
repository FDL algorithm because the inputs in this experiment are Woodruff's
FDLs, not independently computed team FDLs. LDS rasters were inventoried but
not evaluated in this run.

Remaining evidence needed:

1. Woodruff's PC1 raster for these exact years and boundary, together with its
   masking, scaling, sign and score-projection conventions. Compare on the same
   pixels, accounting explicitly for sign and centering; report correlation,
   residuals and spatial differences. Agree acceptance tolerances first.
2. Historical daily input product/collection and FDL processing settings, or
   matching daily inputs for at least one year. Recompute team FDL and report
   exact match fraction, date errors, code differences and maps of discrepancies.
3. Confirmation of boundary identity and the expected retained pixel mask.
4. Sponsor agreement on scientific acceptance criteria and unresolved D06.

## Reproduction and artifacts

From `api/`, use the documented project environment, install
`requirements-validation.txt` in addition to `requirements.txt`, then run:

```powershell
python -m jobs.validate_woodruff --archive 'C:/Users/ossoc/Downloads/OneDrive_1_10-13-2026.zip'
```

This run used the existing `demo/.venv/Scripts/python.exe` environment with
the required geospatial libraries installed. Exact runtime versions and
per-year statistics are in `woodruff-validation-2026-10-13-results.json`.
Generated `api/output/woodruff_validation/pc1_covariance.tif`,
`pc1_correlation.tif` and `results.json` remain gitignored. Keep the original
archive in shared data storage and record its location in the portfolio.

The archive, report copies and generated outputs were subsequently collected
under `db/validation/woodruff/` on October 13. Its README indexes the files and
its manifest records verified SHA256 hashes. The original Downloads archive
remains unchanged. This local collection is gitignored; instructor access and
OneDrive synchronization are not verified by this operation.
