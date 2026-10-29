from fastapi import APIRouter

import config
from config import BOUNDARIES_DIR
from server import catalog
from snow import store
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
    boundary = catalog.load_boundary(watershed_id)
    return {
            "id": watershed_id, 
            "name": boundary.properties.get("name"), 
            "huc8": boundary.properties.get("huc8"),
            "area_km2": boundary.properties.get("areasqkm"), 
            "geometries": boundary.geometries
        }


@router.get("/{watershed_id}/years")
def get_years(watershed_id: str, threshold: float = 10):
    """Years with stored FDL for every MODIS tile the watershed touches; these can go into POST /pca."""
    shed = catalog.load_watershed(watershed_id)
    return {
            "watershed_id": watershed_id,
            "threshold": threshold,
            "tiles": shed.tiles,
            "years": store.stored_years(config.FDL_STORE_DIR, shed.tiles, threshold)
        }
