# Glossary

Quick reference for the project's method and watershed terms. Where a term depends on an open decision, its number is given (e.g. D06); see `Planning/decisions.md`. Status as of 2026-10-29.

## Watersheds

**HUC (Hydrologic Unit Code)**
The USGS ID for a drainage area. More digits = smaller area. HUC8 is the likely choice (D08).

| Level | Name |
|---|---|
| HUC6 | Basin |
| HUC8 | Subbasin (e.g. 17050113, South Fork Boise) |
| HUC10 | Watershed |
| HUC12 | Subwatershed |

**WBD (Watershed Boundary Dataset)**
The USGS standard dataset of watershed boundaries.

**Mask**
A true/false raster marking which pixels are inside the watershed. A pixel counts if its center is inside the boundary; `all_touched` (any pixel the boundary touches) is the alternative.

**Cross-state watershed**
A watershed extending outside Idaho. 60 of the 92 HUC8s touching Idaho do, so the precompute must cover more than the state.

## FDL and LDS

**NDSI threshold**
The cut-off that turns the satellite's snow index into snow / not snow. Default **10** (snow ≥ 10) (D01).

**DOY (day of year)**
1 = January 1. FDL and LDS are stored as DOY. DOY 91 = April 1.

**FDL (first day land)**
For each pixel and year, the first day of the melt season the pixel is seen snow-free. The input to PCA. Called **FTL** in the September 15 meeting; same thing.

**LDS (last day snow)**
The last day snow was seen before FDL. Melt-out happened between LDS and FDL.

**Start date (DOY 91)**
Where the FDL search begins. It searches forward for pixels with snow that day, and backward for pixels already clear (D04).

**FDL special values**
**0** = never snow, **365** = never melted, **−1** = never observed. All are masked out before PCA.

**FDL store / precompute**
FDL rasters computed once per tile per year and saved (`db/fdl_store/`), so user requests only run the fast PCA (D13).

## PCA

**D matrix**
The PCA input. **Rows = pixels, columns = years.** Each column is one year's FDL raster flattened.

**PCA (principal component analysis)**
Finds the main patterns of variation. Years are the variables and pixels are the observations.

**PC1**
The first, strongest component: the recurring melt pattern, and the tool's main output.

**Pixel scores**
Each pixel's PC1 value, put back on the grid to make the map. **Dark = earlier melt, light = later.** Values are relative melt timing, not dates.

**Loadings / weights**
PC1's per-year values: how much each year contributes. Not mappable.

**Explained variance**
The share of variation PC1 captures (about 93% in the team's runs).

**Covariance vs. correlation PCA**
Covariance centers each year; correlation also rescales each year so all count equally. Covariance is the current default; unresolved (D06).

**Sign rule**
PC1 is flipped if needed so higher PC1 = later melt.

## Cloud-gap filling (stretch goal)

**Cloud-gap filling**
Estimating snow under clouds for a chosen day.

**Cut-off τ (tau)**
A PC1 threshold: above τ is predicted snow, below is land. Chosen to best match the pixels visible that day, then applied to the cloudy ones.
