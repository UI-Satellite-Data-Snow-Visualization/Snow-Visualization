"""The copies in api/snow/ give identical output to the originals kept in archive/."""
import importlib.util
import sys
from pathlib import Path

import numpy as np

import snow
from snow import fdl as F

ARCHIVE = Path(__file__).resolve().parents[2] / "archive"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def archived_snowpca():
    sys.path.insert(0, str(ARCHIVE / "demo"))
    try:
        import snowpca
        return snowpca
    finally:
        sys.path.pop(0)


def test_pca_pipeline_identical():
    old = archived_snowpca()
    a = old.make_dummy_fdl_stack(shape=(90, 70), n_years=12, seed=5)
    b = snow.make_dummy_fdl_stack(shape=(90, 70), n_years=12, seed=5)
    for ra, rb in zip(a.rasters, b.rasters):
        assert np.array_equal(ra, rb, equal_nan=True)
    Da, ia = old.build_matrix(a.rasters, min_valid_frac=0.9)
    Db, ib = snow.build_matrix(b.rasters, min_valid_frac=0.9)
    assert np.array_equal(Da, Db)
    pa = old.to_raster(old.run_pca(Da).pc(1), ia)
    pb = snow.to_raster(snow.run_pca(Db).pc(1), ib)
    assert np.array_equal(pa, pb, equal_nan=True)


def test_fdl_identical():
    old = load("archived_fdl", ARCHIVE / "realdata" / "fdl.py")
    rng = np.random.default_rng(2)
    codes = np.array([0, 5, 9, 10, 40, 100, 200, 201, 211, 237, 239, 250, 254, 255], np.uint8)
    stack = rng.choice(codes, size=(120, 20, 15))
    doys = np.arange(40, 160)
    for a, b in zip(old.fdl_lds(stack, doys, 10, 91), F.fdl_lds(stack, doys, 10, 91)):
        assert np.array_equal(a, b)
