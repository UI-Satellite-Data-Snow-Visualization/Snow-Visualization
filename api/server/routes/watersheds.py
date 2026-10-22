from fastapi import APIRouter

from config import BOUNDARIES_DIR
from snow import watershed as ws

router = APIRouter(tags=["watersheds"])


@router.get("")
def list_watersheds():
    out = []
    for path in sorted(BOUNDARIES_DIR.glob("*.geojson")):
        props = ws.load_boundary(path).properties
        out.append({"id": path.stem, "name": props.get("name"), "huc8": props.get("huc8"),
                    "area_km2": props.get("areasqkm")})
    return out
