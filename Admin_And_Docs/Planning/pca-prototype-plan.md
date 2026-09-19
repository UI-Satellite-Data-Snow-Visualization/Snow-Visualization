# PCA prototype plan

Draft experiment proposal, September 17, 2026. The September 15 [meeting](../Meeting_Notes/1_Meeting_9_15_26.docx) requests a synthetic pixels-by-years matrix, column standardization, PCA, PC1 extraction, and image reconstruction. The specific experiments and criteria below are engineering recommendations, not sponsor requirements. No prototype is implemented yet.

## Baseline experiment

1. Create a small two-dimensional grid with a known early-to-late spatial timing gradient. Save shape, pixel order, and a fixed random seed.
2. Generate annual timing columns from that gradient with positive annual scale factors and annual offsets. Begin without noise; add seeded noise in a separate case. Synthetic values are illustrative, not observed melt dates.
3. Flatten each annual raster using the same row/column order to form X with pixels as rows and years as columns. Keep a reversible mapping from retained rows to original pixels.
4. Standardize each year across retained pixels to mean zero and unit standard deviation. Record the standard-deviation convention. Reject or explicitly exclude zero-variance years; do not divide by zero.
5. Fit PCA with years as features. For centered standardized Z = U S Vᵀ, the spatial PC1 scores are Z v₁ = U[:, 1] s₁ (mathematical one-based component indexing). The year loadings alone cannot be reshaped into a pixel raster.
6. Orient the score sign consistently so higher values correspond to later synthetic timing. Record the rule; PCA sign is arbitrary. Report explained variance using squared singular values divided by their total.
7. Restore scores to the original raster layout, reinstating masked pixels. Retain geospatial metadata when real raster inputs become available.

## Proposed checks

| Case | Evidence expected |
| --- | --- |
| Noiseless shared pattern | Absolute correlation with the known nonconstant pattern approaches 1 and PC1 explains nearly all variance, within recorded numerical tolerance. |
| Seeded noise | Report correlation, explained variance, and pattern error across noise levels; no assumed 85% or 97% target. |
| Layout round trip | A grid with unique pixel identifiers reconstructs exactly; verify more than visual similarity. |
| PCA reconstruction | Full retained-component reconstruction matches standardized inputs within numerical tolerance; PC1-only reconstruction is explicitly an approximation. |
| Sign reversal | Flipping raw eigenvector sign leaves the documented display orientation consistent. |
| Constant or insufficient input | Zero-variance years, too few valid rows/years, and all-masked rasters return explicit diagnostics. |
| Missing pixels | Begin with a documented common valid-pixel mask across years. Verify mask restoration; any imputation is a separate experiment requiring justification. |
| Misaligned rasters | Detect differences in CRS, transform, resolution, dimensions, and pixel order before stacking. Do not silently resample. |

The common-mask baseline may discard substantial real data. Measure retained coverage and resolve the production policy through D05/D06 in [decisions.md](decisions.md).

## Transition to sponsor samples

Record source identifiers, years, sensor/product, threshold, quality rules, and first-land algorithm version. Verify shared raster geometry before constructing the matrix. Compare a small sample against sponsor reference outputs or independently checked calculations, including melt-date encoding and missing values. Compare standardized and centered-only PCA as a sensitivity experiment; the meeting's standardization proposal is not proof that both methods are equivalent.

Deliver the reproducible script or notebook, dependency versions and verified run command once implemented, synthetic fixtures, diagnostic outputs, and a short findings report. Keep large satellite files and credentials outside version control. Select implementation dependencies during prototype implementation; this plan does not establish the application stack.
