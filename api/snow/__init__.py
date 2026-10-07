"""Recurrent snowmelt pattern via PCA (Woodruff & Qualls, 2019). Scaffold."""
from .synthetic import DummyStack, make_dummy_fdl_stack
from .matrix import PixelIndex, build_matrix, to_raster
from .pca import PCAResult, pc_as_doy, run_pca, summarize

__all__ = ["DummyStack", "make_dummy_fdl_stack", "PixelIndex", "build_matrix",
           "to_raster", "PCAResult", "run_pca", "pc_as_doy", "summarize"]
