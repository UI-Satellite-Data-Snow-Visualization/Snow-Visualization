"""Satellite snow products the tool can ingest, and the native grid of each.

Every product shares the MODIS sinusoidal tiling (same hXXvYY tile edges and
origin); only the pixels per tile differ: MODIS 2400 (~463 m), VIIRS 3000
(~371 m). Product keys ("MOD10A1F.061", "VNP10A1F.002") are the storage keys
used in db/fdl_store/snow.sqlite3, so sensors never mix in one PCA (D03).

Which VIIRS product the sponsor wants is still open (D02). VNP10A1F (Suomi
NPP, from 2012) is the default VIIRS choice because the sponsor asked for
VIIRS from 2012; VJ110A1F (NOAA-20, from 2018) is registered as well.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import chunks
from . import watershed as ws


@dataclass(frozen=True)
class Product:
    key: str             # storage key: SHORTNAME.collection
    short_name: str      # NASA CMR short name
    version: str         # NASA CMR version
    collection: str      # collection as written in file names
    sensor: str          # "MODIS" or "VIIRS"
    platform: str
    label: str
    layer: str           # daily gap-filled NDSI layer used for FDL
    extension: str       # ".hdf" (HDF4) or ".h5" (HDF5)
    tile_pixels: int
    first_year: int      # first year with data in the archive
    missing_codes: tuple[int, ...]   # documented "unknown" flags (provenance only)
    aliases: tuple[str, ...] = ()

    @property
    def pixel_size(self) -> float:
        return ws.TILE_SIZE_M / self.tile_pixels

    @property
    def grid(self) -> chunks.ProductGrid:
        return chunks.ProductGrid(self.key, self.pixel_size, self.tile_pixels,
                                  ws.GRID_ORIGIN_X, ws.GRID_ORIGIN_Y, ws.MODIS_CRS)

    def granule_pattern(self, year: int, tile: str) -> str:
        """CMR granule-name pattern for one tile-year."""
        return f"{self.short_name}.A{year}*.{tile}.{self.collection}.*"

    def summary(self) -> dict:
        return {"key": self.key, "label": self.label, "sensor": self.sensor,
                "platform": self.platform, "short_name": self.short_name,
                "collection": self.collection, "layer": self.layer,
                "first_year": self.first_year, "pixel_size_m": round(self.pixel_size, 3),
                "tile_pixels": self.tile_pixels}


MODIS = Product(
    key=chunks.PRODUCT, short_name="MOD10A1F", version="61", collection="061",
    sensor="MODIS", platform="Terra", label="MODIS Terra · MOD10A1F v61 (500 m)",
    layer="CGF_NDSI_Snow_Cover", extension=".hdf", tile_pixels=ws.TILE_PIXELS_500M,
    first_year=2000, missing_codes=(200, 201, 211, 250, 254, 255), aliases=("modis",),
)
# VIIRS flag codes (VNP10A1 v002 layer description): 201 no decision, 211 night,
# 250 cloud, 251 missing, 252 L1B unusable, 253 bowtie trim, 254 L1B fill, 255 fill.
# 237 inland water and 239 ocean mean the same as in MODIS.
VIIRS_MISSING = (201, 211, 250, 251, 252, 253, 254, 255)
VIIRS_NPP = Product(
    key="VNP10A1F.002", short_name="VNP10A1F", version="2", collection="002",
    sensor="VIIRS", platform="Suomi NPP", label="VIIRS Suomi NPP · VNP10A1F v2 (375 m)",
    layer="CGF_NDSI_Snow_Cover", extension=".h5", tile_pixels=3000,
    first_year=2012, missing_codes=VIIRS_MISSING, aliases=("viirs", "vnp", "npp"),
)
VIIRS_NOAA20 = Product(
    key="VJ110A1F.002", short_name="VJ110A1F", version="2", collection="002",
    sensor="VIIRS", platform="NOAA-20", label="VIIRS NOAA-20 · VJ110A1F v2 (375 m)",
    layer="CGF_NDSI_Snow_Cover", extension=".h5", tile_pixels=3000,
    first_year=2018, missing_codes=VIIRS_MISSING, aliases=("vj1", "noaa20", "noaa-20"),
)

ALL = (MODIS, VIIRS_NPP, VIIRS_NOAA20)
DEFAULT = MODIS
KEYS = tuple(p.key for p in ALL)


def get(name: str | Product) -> Product:
    """Look up a product by key, short name or alias (case-insensitive)."""
    if isinstance(name, Product):
        return name
    wanted = str(name).strip().lower()
    for p in ALL:
        if wanted in (p.key.lower(), p.short_name.lower(), *p.aliases):
            return p
    raise ValueError(f"Unknown product {name!r}. Choose one of: {', '.join(KEYS)} "
                     f"(or modis / viirs).")


def for_file(filename: str) -> Product:
    """Product of a daily granule, from its file name."""
    short = filename.split(".", 1)[0]
    for p in ALL:
        if p.short_name == short:
            return p
    raise ValueError(f"{filename}: not a registered product")
