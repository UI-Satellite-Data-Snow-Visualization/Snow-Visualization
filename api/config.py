"""Where the api finds stored data. The db/ layer holds files only; code lives here.

SNOW_DB points at the storage root (default: the repo's db/ folder). In Docker
this becomes a mounted volume, so the api and the stored data deploy separately.
"""
import os
from pathlib import Path

DB_DIR = Path(os.environ.get("SNOW_DB", Path(__file__).resolve().parent.parent / "db"))
BOUNDARIES_DIR = DB_DIR / "boundaries"   # watershed GeoJSON (committed)
FDL_STORE_DIR = DB_DIR / "fdl_store"     # precomputed FDL/LDS rasters (gitignored)
RAW_DIR = DB_DIR / "raw"                 # raw HDF download cache (gitignored, safe to delete)
