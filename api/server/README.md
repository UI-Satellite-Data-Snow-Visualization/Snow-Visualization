# api/server

FastAPI web server. Run from `api/`:

```
uvicorn server.main:app --reload
```

Then open http://localhost:8000/docs for every route, with request/response schemas and a "Try it out" button.

## Endpoints

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | `{"status": "ok"}` |
| GET | `/watersheds` | id, name, HUC8 and area of every boundary in `db/boundaries/` |
| GET | `/watersheds/{id}` | the same plus the boundary geometries (lon/lat), for drawing on the map |
| GET | `/watersheds/{id}/years?threshold=10` | MODIS tiles the watershed touches, and the years with stored FDL for all of them |
| POST | `/pca` | runs PCA: `{"watershed_id", "years", "scaling": "covariance" \| "correlation", "threshold"}` → variance explained, per-year weight and correlation, pixel counts, `result_id`, and the two URLs below |
| GET | `/pca/{result_id}/pc1.tif` | PC1 GeoTIFF on the native MODIS grid, float32, NaN = no data, with provenance tags |
| GET | `/pca/{result_id}/preview.png` | PC1 as a colored RGBA PNG in Web Mercator (dark = earlier melt), transparent outside the watershed; place it on the map with `preview_bounds` from the POST response |

## How it fits together

- `routes/`: thin HTTP layer. Validates input (`schemas.py`), calls the modules below, maps errors to 404/422.
- `catalog.py`: finds a boundary by id (refuses ids that point outside `db/boundaries/`) and caches its mask on the MODIS grid.
- `pca_service.py`: the steps of `jobs/run_real.py`, reading from the FDL store instead of daily files (`snow/store.py`, which also joins watersheds that span two tiles). Results are cached in memory (32 most recent), so the GeoTIFF and preview don't rerun the PCA. Restarting the server or running several workers means a `result_id` may be unknown; the client should POST again on a 404.
- Pixels are kept if their center is inside the boundary and they have a valid FDL (not 0, 365 or no data) in every chosen year.

**Data needed:** `/pca` reads `db/fdl_store/` (`SNOW_DB` env var, see `../config.py`). Fill it with `python -m jobs.precompute_fdl --years ... --tiles h09v04`; until then `/watersheds/{id}/years` returns an empty list and `/pca` returns 422. The tests use a synthetic store instead (`tests/test_pca_api.py`).
