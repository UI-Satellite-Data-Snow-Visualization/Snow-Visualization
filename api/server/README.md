# api/server

The web server. **Not started**; the stack is undecided (D09).

Planned role: load the precomputed FDL rasters from `db/` into memory at startup, and answer requests:
1. List watersheds (from `db/boundaries/`).
2. For a watershed, sensor, years and threshold: crop the stored FDLs, build the D matrix, run PCA (`snow/`), and return PC1 as a map image for the client.
3. Return the same PC1 as a georeferenced GeoTIFF on the native MODIS grid, on request.

Target: tens of milliseconds per request for a HUC8. PCA itself takes about 5–30 ms at HUC8 size; reading files per request is what to avoid.
