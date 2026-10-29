"""Request and response models. FastAPI validates against these and lists them in /docs."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PCARequest(BaseModel):
    watershed_id: str = Field(examples=["wbd_huc8_17050113"])
    years: list[int] = Field(examples=[[2020, 2021, 2022, 2023, 2024]])
    scaling: Literal["covariance", "correlation"] = "covariance"   # D06 is still open
    threshold: float = 10

    @field_validator("years")
    @classmethod
    def at_least_two_years(cls, years: list[int]) -> list[int]:
        years = sorted(set(years))
        if len(years) < 2:
            raise ValueError("PCA needs at least 2 different years.")
        return years


class YearStats(BaseModel):
    year: int
    weight: float        # PC1 eigenvector entry for this year
    correlation: float   # correlation of this year's FDL with PC1


class Bounds(BaseModel):
    west: float
    south: float
    east: float
    north: float


class PCAResponse(BaseModel):
    result_id: str
    watershed_id: str
    name: str | None
    years: list[int]
    scaling: str
    threshold: float
    pixel_rule: str
    pixels_in_watershed: int
    pixels_used: int     # pixels with a valid FDL in every year
    variance_explained: list[float]   # PC1, PC2, ... as fractions
    year_stats: list[YearStats]
    preview_bounds: Bounds            # lon/lat edges for placing preview.png on a web map
    geotiff_url: str
    preview_url: str
