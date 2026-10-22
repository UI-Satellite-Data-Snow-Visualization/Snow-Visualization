from fastapi import APIRouter, HTTPException

from config import BOUNDARIES_DIR
from snow import watershed as ws

router = APIRouter(tags=["watersheds"])


@router.get("")
def list_watersheds():
    out = []
    for path in sorted(BOUNDARIES_DIR.glob("*.geojson")):
        props = ws.load_boundary(path).properties
        out.append({
                "id": path.stem, 
                "name": props.get("name"), 
                "huc8": props.get("huc8"),
                "area_km2": props.get("areasqkm")
            })
    return out

@router.get("/{watershed_id}")
def get_watershed(watershed_id: str):
    path = (BOUNDARIES_DIR / f"{watershed_id}.geojson").resolve()
    # The id becomes a file name, so refuse anything that points outside db/boundaries/.
    if path.parent != BOUNDARIES_DIR.resolve() or not path.exists():
        raise HTTPException(status_code=404, detail=f"Watershed {watershed_id} not found")
    boundary = ws.load_boundary(path)
    return {
            "id": watershed_id, 
            "name": boundary.properties.get("name"), 
            "huc8": boundary.properties.get("huc8"),
            "area_km2": boundary.properties.get("areasqkm"), 
            "geometries": boundary.geometries
        }