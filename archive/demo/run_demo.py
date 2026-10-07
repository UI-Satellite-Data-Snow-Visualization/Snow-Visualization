"""Run the PCA pipeline on dummy data at several matrix sizes.

    python run_demo.py            # prints results, saves pc1_demo.png next to this script

The figure needs matplotlib; without it the numeric results still print.
"""
from pathlib import Path

import numpy as np

from snowpca import build_matrix, make_dummy_fdl_stack, pc_as_doy, run_pca, summarize, to_raster

CASES = [  # (raster height, width, number of years)
    (40, 30, 8),
    (120, 90, 17),   # roughly the paper's setup: 17 years
    (250, 200, 25),
]


MIN_VALID_FRAC = 0.9  # keep pixels seen in >=90% of years; gap-fill the rest


def run_case(h, w, n_years, seed=0):
    stack = make_dummy_fdl_stack(shape=(h, w), n_years=n_years, seed=seed)
    D, index = build_matrix(stack.rasters, min_valid_frac=MIN_VALID_FRAC)
    result = run_pca(D)

    pc1_map = to_raster(result.pc(1), index)
    ok = np.isfinite(pc1_map) & np.isfinite(stack.true_pattern)
    recovery = np.corrcoef(pc1_map[ok], stack.true_pattern[ok])[0, 1]

    print(f"\n=== {h}x{w} raster, {n_years} years -> D is {D.shape[0]} x {D.shape[1]} ===")
    print(summarize(result, stack.years))
    inside = int(np.isfinite(stack.true_pattern).sum())
    print(f"Pixels kept: {D.shape[0]} of {inside} inside the watershed")
    print(f"PC1 vs. true pattern correlation: {recovery:.3f}")
    return stack, D, index, result


def save_figure(stack, D, index, result, path=Path(__file__).with_name("pc1_demo.png")):
    try:
        import matplotlib
    except ImportError:
        print("\nmatplotlib not installed; skipping figure (pip install -r requirements.txt).")
        return
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    doy_map = to_raster(pc_as_doy(D, result), index)
    fig, ax = plt.subplots(1, 4, figsize=(16, 4))
    ax[0].imshow(stack.true_pattern, cmap="gray"); ax[0].set_title("True recurrent pattern")
    ax[1].imshow(stack.rasters[0], cmap="gray"); ax[1].set_title(f"FDL {stack.years[0]} (noisy)")
    im = ax[2].imshow(doy_map, cmap="gray"); ax[2].set_title("PC1 as approx. DOY")
    fig.colorbar(im, ax=ax[2], fraction=0.046)
    for a in ax[:3]:
        a.set_xticks([]); a.set_yticks([])
    n = len(result.explained_variance_ratio)
    ax[3].bar(range(1, n + 1), result.explained_variance_ratio * 100)
    ax[3].set_xlabel("Principal component"); ax[3].set_ylabel("% variance"); ax[3].set_title("Scree plot")
    fig.tight_layout(); fig.savefig(path, dpi=110)
    print(f"\nSaved {path}")


if __name__ == "__main__":
    results = [run_case(*c) for c in CASES]
    save_figure(*results[1])
