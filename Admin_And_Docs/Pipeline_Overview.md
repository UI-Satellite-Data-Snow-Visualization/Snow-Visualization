# Data pipeline, start to finish

How satellite snow data becomes a recurring-snowmelt map, and which file in `api/` does each step. GitHub renders the diagrams below; in VS Code, use a Mermaid preview extension.

Legend: **solid boxes are built**, *dashed boxes are planned* (not built yet). Status as of 2026-11-11.

## 1. The big picture

The work splits into two halves. The **offline precompute** is slow (minutes per tile-year) and runs once per year of data. The **user request** is fast (seconds) and runs every time someone picks a watershed.

```mermaid
flowchart TD
    subgraph OFFLINE["OFFLINE PRECOMPUTE: once per tile-year (api/jobs/precompute_fdl.py)"]
        A["NSIDC / NASA Earthdata, one file per tile per day<br/>MODIS MOD10A1F v61: HDF4, 2400 x 2400, ~463 m<br/>VIIRS VNP10A1F / VJ110A1F v2: HDF5, 3000 x 3000, ~371 m"]
        B["Read CGF_NDSI_Snow_Cover layer (snow/granules.py)<br/>stack days: (days, rows, cols) uint8<br/>raw file deleted right after reading"]
        C["Classify each pixel each day<br/>snow = NDSI 10 to 100<br/>clear = NDSI below 10, or inland water 237<br/>missing = cloud/night/fill flags"]
        D["FDL / LDS search per pixel<br/>snow/fdl.py fdl_lds(), start DOY 91<br/>(see section 2)"]
        E[("db/fdl_store/snow.sqlite3<br/>FDL + LDS, thresholds 10-50<br/>200 x 200 int16 chunks per product,<br/>on its native sinusoidal grid")]
        A -->|earthaccess download| B --> C --> D --> E
    end

    subgraph REQUEST["USER REQUEST: per watershed (api/server/pca_service.py)"]
        U["User picks watershed,<br/>sensor, and years"]
        W[("db/boundaries/<br/>WBD HUC8 GeoJSON, lon/lat")]
        M["Watershed mask<br/>snow/watershed.py<br/>reproject boundary to sinusoidal,<br/>rasterize onto the product's pixel grid"]
        K["Clip each year's FDL raster to the mask<br/>drop 0 never-snow, 365 never-melted, -1 no-data"]
        X["D matrix: snow/matrix.py build_matrix()<br/>rows = pixels (M), columns = years (N)"]
        P["PCA: snow/pca.py run_pca()<br/>years are variables, pixels are observations"]
        S["PC1 pixel scores = recurrent melt pattern<br/>to_raster() puts them back on the grid"]
        U --> W --> M --> K --> X --> P --> S
    end

    E -->|"one FDL raster per year"| K

    subgraph OUT["OUTPUTS"]
        G["PC1 GeoTIFF<br/>native MODIS or VIIRS grid, georeferenced<br/>(user download)"]
        V["Map preview<br/>reprojected to Web Mercator for display only<br/>dark = early melt, light = late"]
        WEB["Browser page: preview + download<br/>api/server/ + client/ (map still planned)"]
        CGF["Stretch: cloud-gap fill a chosen day<br/>threshold on PC1 fit to visible pixels"]:::planned
    end

    S --> G
    S --> V
    G --> WEB
    V --> WEB
    S -.-> CGF

    classDef planned stroke-dasharray: 5 5
```

Two ways in: the FastAPI server reads the stored FDLs, so users never wait on the daily-imagery scan. `run_real.py` and the workbench (`jobs/tui.py`) instead compute FDL from raw files in `db/raw/` (downloaded by `jobs/download.py`). Same math: on 2026-11-10, for each sensor (MODIS and VIIRS), all three gave identical FDL for 2023–2024 (South Fork Boise).

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
| Precompute FDL/LDS into the store | `jobs/precompute_fdl.py`, `snow/chunks.py` | `python -m jobs.precompute_fdl --years 2020 2021 2022` (add `--product viirs` for VIIRS) |
| Read daily files (HDF4 / HDF5), product grids | `snow/granules.py`, `snow/products.py` | `python -m jobs.inspect_granule PATH` |
| FDL/LDS algorithm | `snow/fdl.py` `fdl_lds()` | |
| Watershed mask, grid, GeoTIFF writer | `snow/watershed.py` | |
| D matrix and back | `snow/matrix.py` `build_matrix()`, `to_raster()` | |
| PCA | `snow/pca.py` `run_pca()` | |
| End-to-end prototype (one watershed) | `jobs/run_real.py` | `python -m jobs.run_real --years 2020 2021 2022 2023 2024` |
| Local workbench | `jobs/tui.py`, `jobs/pixel_map.py` | `python -m jobs.tui` |
| Web server / front end | `server/`, `client/` | `python -m uvicorn server.main:app --reload`; in `client/`: `npm run dev` |

Open choices that affect this pipeline are tracked in `Planning/decisions.md`: covariance vs. correlation PCA (D06), HUC level and pixel inclusion rule (D08), stack (D09, not formally recorded) and VIIRS product (D02). Watersheds that span more than one tile are already handled: `snow/store.py` joins the stored tiles when it reads.
