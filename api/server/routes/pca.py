from fastapi import APIRouter, HTTPException, Response

from server import catalog, pca_service
from server.schemas import PCARequest, PCAResponse, YearStats

router = APIRouter(tags=["pca"])


@router.post("", response_model=PCAResponse)
def create_pca(req: PCARequest):
    try:
        run = pca_service.run(req.watershed_id, req.years, req.scaling, req.threshold)
    except ValueError as err:   # missing years, no complete pixels, too few pixels
        raise HTTPException(status_code=422, detail=str(err)) from err
    result = run.result
    return PCAResponse(
        result_id=run.result_id,
        watershed_id=run.watershed.id,
        name=run.watershed.boundary.properties.get("name"),
        years=run.years,
        scaling=run.scaling,
        threshold=run.threshold,
        pixel_rule=catalog.PIXEL_RULE,
        pixels_in_watershed=int(run.watershed.mask.sum()),
        pixels_used=run.pixels_used,
        variance_explained=result.explained_variance_ratio.tolist(),
        year_stats=[YearStats(year=y, weight=w, correlation=c) for y, w, c in
                    zip(run.years, result.weights(1).tolist(), result.year_correlations[:, 0].tolist())],
        preview_bounds=run.preview_bounds,
        geotiff_url=f"/pca/{run.result_id}/pc1.tif",
        preview_url=f"/pca/{run.result_id}/preview.png",
    )


@router.get("/{result_id}/pc1.tif")
def download_pc1(result_id: str):
    run = _cached(result_id)
    name = f"pc1_{run.watershed.id}_{run.years[0]}-{run.years[-1]}_{run.scaling}.tif"
    return Response(pca_service.geotiff_bytes(run), media_type="image/tiff",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/{result_id}/preview.png")
def preview(result_id: str):
    return Response(_cached(result_id).preview_png, media_type="image/png")


def _cached(result_id: str) -> pca_service.PCARun:
    run = pca_service.get(result_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Result not found or expired; POST /pca again.")
    return run
