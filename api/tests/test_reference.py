"""snow/fdl.py gives the same FDL/LDS as Woodruff's starter code (reference/).

The starter code reads HDF files through xarray; here xarray.open_dataset is
swapped for in-memory datasets holding raw uint8 codes, so the starter's own
algorithm and GeoTIFF writer run unchanged. The one intended difference:
pixels never observed as snow or clear get 0 in the starter and NODATA here.
"""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

xr = pytest.importorskip("xarray")
pytest.importorskip("rioxarray")
rasterio = pytest.importorskip("rasterio")

from snow import fdl as F   # noqa: E402

STARTER = Path(__file__).resolve().parents[2] / "reference" / "Starter_Code_FDL_LDS_MOD10A1F.py"
META = ("UpperLeftPointMtrs=(-10007554.677000,5559752.598333)\n"
        "LowerRightMtrs=(-10003848.175268,5556046.096601)\n"
        "XDim={w}\n\t\tYDim={h}\n")


def load_starter():
    spec = importlib.util.spec_from_file_location("starter_fdl", STARTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def synthetic_season(seed=1, days=160, h=12, w=10):
    """Snow early, land later, with clouds, flags, water, ocean and a never-seen pixel."""
    rng = np.random.default_rng(seed)
    doys = np.arange(40, 40 + days)
    melt = rng.integers(60, 190, size=(h, w))
    stack = np.where(doys[:, None, None] < melt, rng.integers(10, 101, (days, h, w)),
                     rng.integers(0, 10, (days, h, w))).astype(np.uint8)
    flags = np.array([200, 201, 211, 250, 250, 250, 254, 255], np.uint8)
    hide = rng.random(stack.shape) < 0.3
    stack[hide] = rng.choice(flags, hide.sum())
    stack[:, 0, 0] = F.OCEAN
    stack[:, 0, 1] = 250                 # never observed
    stack[:, 0, 2] = F.INLAND_WATER
    return doys, stack


def test_matches_starter_code(tmp_path, monkeypatch):
    starter = load_starter()
    doys, stack = synthetic_season()
    _, h, w = stack.shape
    year = 2001

    datasets = {}
    for doy, day in zip(doys, stack):
        name = tmp_path / "in" / f"MOD10A1F.A{year}{doy:03d}.h09v04.061.2020000000000.hdf"
        name.parent.mkdir(exist_ok=True)
        name.touch()
        datasets[str(name)] = xr.Dataset(
            {"CGF_NDSI_Snow_Cover": (("YDim:MOD_Grid_Snow_500m", "XDim:MOD_Grid_Snow_500m"), day)},
            attrs={"StructMetadata.0": META.format(w=w, h=h)},
        )
    monkeypatch.setattr(starter.xr, "open_dataset", lambda f, **kw: datasets[str(Path(f))])

    starter.process_seasonal_composites_multi_threshold(
        hdf_dir=str(tmp_path / "in"), year=year, thresholds=[10], output_dir=str(tmp_path / "out"), start_doy=91)
    with rasterio.open(tmp_path / "out" / f"FDL_threshold_stack_{year}.tif") as r:
        want_fdl = r.read(1)
    with rasterio.open(tmp_path / "out" / f"LDS_threshold_stack_{year}.tif") as r:
        want_lds = r.read(1)

    fdl, lds = F.fdl_lds(stack, doys, threshold=10, start_doy=91)

    never_seen = (fdl == F.NODATA)
    assert never_seen.sum() == 1 and never_seen[0, 1]
    assert want_fdl[0, 1] == 0 and want_lds[0, 1] == 0      # the starter's ambiguous 0
    assert np.array_equal(fdl[~never_seen], want_fdl[~never_seen])
    assert np.array_equal(lds[~never_seen], want_lds[~never_seen])
    # The season exercises both search directions, not just one.
    assert (fdl > 91).any() and ((fdl > 0) & (fdl < 91)).any()
