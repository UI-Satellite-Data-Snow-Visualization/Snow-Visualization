# Data pipeline, start to finish

How satellite snow data becomes a recurring-snowmelt map, and which file in `api/` does each step. GitHub renders the diagrams below; in VS Code, use a Mermaid preview extension.

Legend: **solid boxes are built**, *dashed boxes are planned* (not built yet). Status as of 2026-10-20.

## 1. The big picture

The work splits into two halves. The **offline precompute** is slow (minutes per tile-year) and runs once per year of data. The **user request** is fast (seconds) and runs every time someone picks a watershed.

```mermaid
flowchart TD
    subgraph OFFLINE["OFFLINE PRECOMPUTE: once per tile-year (api/jobs/precompute_fdl.py)"]
        A["NSIDC / NASA Earthdata<br/>MOD10A1F v61, one HDF4 file per tile per day<br/>2400 x 2400 pixels, 500 m, ~244 files per year"]
        B["Read CGF_NDSI_Snow_Cover layer<br/>stack days: (days, 2400, 2400) uint8<br/>raw file deleted right after reading"]
        C["Classify each pixel each day<br/>snow = NDSI 10 to 100<br/>clear = NDSI below 10, or inland water 237<br/>missing = cloud/night/fill flags"]
        D["FDL / LDS search per pixel<br/>snow/fdl.py fdl_lds(), start DOY 91<br/>(see section 2)"]
        E[("db/fdl_store/<br/>fdl_TILE_YEAR_t10.tif<br/>lds_TILE_YEAR_t10.tif<br/>int16 DOY, MODIS sinusoidal grid")]
        A -->|earthaccess download| B --> C --> D --> E
    end

    subgraph REQUEST["USER REQUEST: per watershed (prototype: api/jobs/run_real.py)"]
        U["User picks watershed,<br/>sensor, and years"]:::planned
        W[("db/boundaries/<br/>WBD HUC8 GeoJSON, lon/lat")]
        M["Watershed mask<br/>snow/watershed.py<br/>reproject boundary to sinusoidal,<br/>rasterize onto the MODIS pixel grid"]
        K["Clip each year's FDL raster to the mask<br/>drop 0 never-snow, 365 never-melted, -1 no-data"]
        X["D matrix: snow/matrix.py build_matrix()<br/>rows = pixels (M), columns = years (N)"]
        P["PCA: snow/pca.py run_pca()<br/>years are variables, pixels are observations"]
        S["PC1 pixel scores = recurrent melt pattern<br/>to_raster() puts them back on the grid"]
        U --> W --> M --> K --> X --> P --> S
    end

    E -->|"one FDL raster per year"| K

    subgraph OUT["OUTPUTS"]
        G["PC1 GeoTIFF<br/>native MODIS grid, georeferenced<br/>(user download)"]
        V["Map preview<br/>reprojected to Web Mercator for display only<br/>dark = early melt, light = late"]
        WEB["Web map + download in the browser<br/>api/server/ + client/ (D09)"]:::planned
        CGF["Stretch: cloud-gap fill a chosen day<br/>threshold on PC1 fit to visible pixels"]:::planned
    end

    S --> G
    S --> V
    G --> WEB
    V --> WEB
    S -.-> CGF

    classDef planned stroke-dasharray: 5 5
```

Note on the prototype: today `run_real.py` computes FDL itself from raw files in `db/raw/` (downloaded by `jobs/download.py`) rather than reading `db/fdl_store/`. Same math, same output; the planned server will read the store so users never wait on the daily-imagery scan.

## 2. What the FDL step does to one pixel in one year

This is the part in `snow/fdl.py` (fixed copy of Woodruff's `reference/Starter_Code_FDL_LDS_MOD10A1F.py`). It runs on every pixel at once with numpy, but the logic for a single pixel is:

```mermaid
flowchart TD
    S0["Day-by-day NDSI codes for one pixel, Jan to Aug"] --> O{"Ocean (239) every day?"}
    O -->|yes| Z0["FDL = 0"]
    O -->|no| ST{"What is it on the start day,<br/>DOY 91 (April 1)?"}
    ST -->|"missing (cloud etc.)"| LOOK["Look forward, then backward,<br/>for the first snow or clear day"]
    LOOK -->|none found| ND["FDL = -1 (no data)"]
    LOOK --> ST2{"snow or clear?"}
    ST -->|snow| FWD
    ST -->|clear| BWD
    ST2 -->|snow| FWD
    ST2 -->|clear| BWD

    FWD["FORWARD search from the start day:<br/>skip missing days, keep track of the last snow day"] --> F1{"Found a clear day?"}
    F1 -->|yes| F2["FDL = first clear day<br/>LDS = last snow day before it<br/>snow that returns later is ignored"]
    F1 -->|"no, snow all season"| F3["FDL = 365 (never melted)"]

    BWD["BACKWARD search from the start day:<br/>already melted, so look back for snow"] --> B1{"Found a snow day?"}
    B1 -->|yes| B2["LDS = that snow day<br/>FDL = the clear day after it"]
    B1 -->|"no, never snow"| B3["FDL = 0 (never snow)"]
```

Before PCA, the codes **0, 365 and -1 are masked out**: they aren't melt dates.

## 3. How the shapes change

Example numbers are the South Fork Boise (HUC8 17050113), 2020-2024, from the 2026-10-06 run.

```mermaid
flowchart LR
    A["Daily files<br/>~244 days x 2400 x 2400<br/>per tile-year"] -->|"fdl_lds()"| B["1 FDL raster<br/>2400 x 2400<br/>per tile-year"]
    B -->|"clip to watershed"| C["5 FDL rasters<br/>H x W each<br/>(one per year)"]
    C -->|"build_matrix()<br/>flatten, keep pixels<br/>inside mask"| D["D matrix<br/>15,741 pixels x 5 years"]
    D -->|"run_pca()"| E["PC1 scores<br/>15,741 values<br/>+ 5 year weights"]
    E -->|"to_raster()"| F["PC1 raster<br/>H x W<br/>= the map"]
```

Things that trip people up:

- **Columns are years, not days.** Each year's whole melt season collapses into one number per pixel (its FDL) before PCA ever sees it.
- **The map is the pixel scores, not the eigenvector.** The eigenvector has one weight per year (how much each year agrees with the pattern); it can't be mapped.
- **PC1 is relative timing.** Darker pixels melt earlier than lighter ones in a typical year. It is not a calendar date or a snow amount.
- **The boundary moves to the raster, never the reverse.** The watershed polygon is reprojected into MODIS sinusoidal and rasterized onto the existing pixels; the satellite data is never resampled. Web Mercator is used only to draw the preview.
- **Every year's raster must be on the identical grid** (same CRS, transform, size, pixel order), or row *i* of D wouldn't be the same place on the ground in every column.

## 4. Where to find each step

| Step | Code | Command (run from `api/`) |
|---|---|---|
| Earthdata login | `jobs/download.py` `login()` | once, see `get_EarthData_Access.md` |
| Download raw daily files | `jobs/download.py` | `python -m jobs.download ...` |
| Precompute FDL/LDS into the store | `jobs/precompute_fdl.py` | `python -m jobs.precompute_fdl --years 2020 2021 2022` |
| FDL/LDS algorithm | `snow/fdl.py` `fdl_lds()` | |
| Watershed mask, grid, GeoTIFF writer | `snow/watershed.py` | |
| D matrix and back | `snow/matrix.py` `build_matrix()`, `to_raster()` | |
| PCA | `snow/pca.py` `run_pca()` | |
| End-to-end prototype (one watershed) | `jobs/run_real.py` | `python -m jobs.run_real --years 2020 2021 2022 2023 2024` |
| Web server / front end | `server/`, `client/` | not started (D09) |

Open choices that affect this pipeline are tracked in `Planning/decisions.md`: covariance vs. correlation PCA (D06), HUC level and pixel inclusion rule (D08), stack (D09), VIIRS product (D02/D03), and tile stitching for watersheds that span more than one MODIS tile.
