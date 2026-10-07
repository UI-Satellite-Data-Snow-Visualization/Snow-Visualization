"""FDL/LDS on hand-built pixels: one case per rule in snow/fdl.py."""
import numpy as np
import pytest

from snow import fdl as F

DOYS = np.arange(80, 121)   # DOY 80-120, start DOY 91
CLOUD, WATER, OCEAN = 250, F.INLAND_WATER, F.OCEAN


def series(*spans, default=CLOUD):
    """Daily codes from (first_doy, last_doy, code) spans; other days get `default`."""
    s = np.full(DOYS.size, default, dtype=np.uint8)
    for first, last, code in spans:
        s[(DOYS >= first) & (DOYS <= last)] = code
    return s


CASES = {   # name: (daily codes, expected FDL, expected LDS)
    "melts forward":           (series((80, 100, 60), (101, 120, 0)), 101, 100),
    "cloud hides melt":        (series((80, 94, 60), (105, 120, 0)), 105, 94),
    "never melts":             (series((80, 120, 80)), F.NEVER_MELTED, F.NEVER_MELTED),
    "melted before start":     (series((80, 85, 60), (86, 120, 0)), 86, 85),
    "never snow":              (series((80, 120, 0)), F.NEVER_SNOW, F.NEVER_SNOW),
    "ocean":                   (series((80, 120, OCEAN)), F.NEVER_SNOW, F.NEVER_SNOW),
    "never observed":          (series(), F.NODATA, F.NODATA),
    "returning snow ignored":  (series((80, 95, 60), (96, 99, 0), (100, 110, 60), (111, 120, 0)), 96, 95),
    "cloudy start, snow next": (series((80, 90, 60), (93, 97, 60), (98, 120, 0)), 98, 97),
    "inland water is clear":   (series((80, 87, 60), (88, 120, WATER)), 88, 87),
    "threshold is inclusive":  (series((80, 100, 10), (101, 120, 9)), 101, 100),
    # Known quirk (CLAUDE.md problem 3, kept on purpose until Woodruff confirms):
    # missing on the start day, clear when first seen, so FDL = start day itself.
    "start-day FDL quirk":     (series((80, 84, 60), (111, 120, 0)), 91, 84),
}


@pytest.mark.parametrize("name", CASES)
def test_case(name):
    codes, want_fdl, want_lds = CASES[name]
    fdl, lds = F.fdl_lds(codes[:, None, None], DOYS, threshold=10, start_doy=91)
    assert (fdl[0, 0], lds[0, 0]) == (want_fdl, want_lds)


def test_all_cases_together():
    """Pixels are independent: running every case in one array gives the same answers."""
    stack = np.stack([c[0] for c in CASES.values()], axis=1)[:, :, None]
    fdl, lds = F.fdl_lds(stack, DOYS, threshold=10, start_doy=91)
    assert fdl[:, 0].tolist() == [c[1] for c in CASES.values()]
    assert lds[:, 0].tolist() == [c[2] for c in CASES.values()]


def test_row_strips_match_whole_tile():
    """precompute_fdl.py runs FDL in row strips to save RAM; results must not change."""
    rng = np.random.default_rng(0)
    codes = np.array([0, 5, 9, 10, 40, 100, 200, 201, 211, 237, 250, 254, 255], np.uint8)
    stack = rng.choice(codes, size=(150, 37, 23))
    doys = np.arange(30, 180)
    whole = F.fdl_lds(stack, doys, 10, 91)
    fdl, lds = np.empty((37, 23), np.int16), np.empty((37, 23), np.int16)
    for r in range(0, 37, 8):
        fdl[r:r + 8], lds[r:r + 8] = F.fdl_lds(stack[:, r:r + 8], doys, 10, 91)
    assert np.array_equal(whole[0], fdl) and np.array_equal(whole[1], lds)
