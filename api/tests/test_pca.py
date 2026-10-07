"""PCA pipeline on synthetic FDL stacks (the checks archive/demo/run_demo.py prints)."""
import numpy as np
import pytest

from snow import build_matrix, make_dummy_fdl_stack, run_pca, to_raster


@pytest.mark.parametrize("h, w, years", [(40, 30, 8), (120, 90, 17), (250, 200, 25)])
@pytest.mark.parametrize("correlation", [False, True])
def test_pc1_recovers_true_pattern(h, w, years, correlation):
    stack = make_dummy_fdl_stack(shape=(h, w), n_years=years, seed=0)
    D, index = build_matrix(stack.rasters, min_valid_frac=0.9)
    result = run_pca(D, use_correlation=correlation)
    pc1 = to_raster(result.pc(1), index)
    ok = np.isfinite(pc1) & np.isfinite(stack.true_pattern)
    assert np.corrcoef(pc1[ok], stack.true_pattern[ok])[0, 1] > 0.99
    assert result.explained_variance_ratio[0] > 0.9


def test_sign_rule_higher_pc1_is_later_melt():
    stack = make_dummy_fdl_stack(n_years=10, seed=3)
    D, _ = build_matrix(stack.rasters, min_valid_frac=0.9)
    result = run_pca(D)
    assert result.weights(1).sum() > 0
    assert np.corrcoef(result.pc(1), D.mean(axis=1))[0, 1] > 0.99
