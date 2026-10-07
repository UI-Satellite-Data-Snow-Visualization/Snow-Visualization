"""PCA on the M x N D matrix, following Woodruff & Qualls (2019), Sec. 3.2.

The N x N covariance (or correlation) matrix of the year columns is
eigendecomposed; each PC is the D matrix projected onto one eigenvector
(their equation 1). PC1 is the recurrent snowmelt pattern.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class PCAResult:
    eigenvalues: np.ndarray               # (N,) descending
    eigenvectors: np.ndarray              # (N, N) column k = year weights for PC k+1
    scores: np.ndarray                    # (M, n_components) column k = PC k+1 per pixel
    explained_variance_ratio: np.ndarray  # (N,)
    year_correlations: np.ndarray         # (N, n_components) corr(year j, PC k)

    def pc(self, k: int = 1) -> np.ndarray:
        """Scores for PC k (1-based, like the paper)."""
        return self.scores[:, k - 1]

    def weights(self, k: int = 1) -> np.ndarray:
        return self.eigenvectors[:, k - 1]


def run_pca(
    D: np.ndarray,
    use_correlation: bool = False,
    center_scores: bool = False,
    n_components: int | None = None,
) -> PCAResult:
    """Run PCA with years as variables and pixels as observations.

    use_correlation: eigendecompose the correlation matrix instead of covariance.
    center_scores: if False (default), project raw D values as in equation 1,
        so PC1 stays on a day-of-year-like scale. If True, project mean-centered D.
    """
    D = np.asarray(D, dtype=float)
    if D.ndim != 2:
        raise ValueError(f"D must be 2D (pixels x years); got shape {D.shape}.")
    m, n = D.shape
    if n < 2:
        raise ValueError("Need at least 2 years (columns).")
    if m <= n:
        raise ValueError(f"Need more pixels than years; got {m} pixels, {n} years.")
    if not np.isfinite(D).all():
        raise ValueError("D contains NaN/inf; clean it in build_matrix first.")

    k = n if n_components is None else int(np.clip(n_components, 1, n))

    mean = D.mean(axis=0)
    Z = D - mean
    scale = np.ones(n)
    if use_correlation:
        scale = D.std(axis=0, ddof=1)
        if np.any(scale == 0):
            raise ValueError("A year column is constant; correlation PCA is undefined.")
        Z = Z / scale

    # Some numpy 2.x BLAS builds on macOS raise spurious divide/overflow warnings
    # from matmul on finite input. Silence them here and check the result instead.
    with np.errstate(all="ignore"):
        cov = (Z.T @ Z) / (m - 1)
    if not np.isfinite(cov).all():
        raise FloatingPointError("Covariance matrix is not finite.")
    evals, evecs = np.linalg.eigh(cov)          # symmetric matrix -> eigh
    order = np.argsort(evals)[::-1]
    evals = np.clip(evals[order], 0, None)
    evecs = evecs[:, order]

    # Eigenvector sign is arbitrary. Flip so weights sum positive, meaning
    # higher PC1 = later melt (matches the paper's dark-early/light-late maps).
    signs = np.sign(evecs.sum(axis=0))
    signs[signs == 0] = 1
    evecs = evecs * signs

    X = Z if center_scores else D / scale
    with np.errstate(all="ignore"):
        scores = X @ evecs[:, :k]
    if not np.isfinite(scores).all():
        raise FloatingPointError("PC scores are not finite.")

    return PCAResult(
        eigenvalues=evals,
        eigenvectors=evecs,
        scores=scores,
        explained_variance_ratio=evals / evals.sum(),
        year_correlations=_column_correlations(D, scores),
    )


def _column_correlations(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Pearson correlation of every column of A with every column of B."""
    Az = (A - A.mean(0)) / A.std(0, ddof=1)
    Bz = (B - B.mean(0)) / B.std(0, ddof=1)
    with np.errstate(all="ignore"):
        return (Az.T @ Bz) / (A.shape[0] - 1)


def pc_as_doy(D: np.ndarray, result: PCAResult, k: int = 1) -> np.ndarray:
    """Rescale PC k to an approximate day of year: D @ w / sum(w).

    Only meaningful when all weights share a sign (true for PC1 in the paper),
    since it is then a weighted average of each pixel's yearly melt dates.
    Handy for a readable map legend; not part of the original method.
    """
    w = result.weights(k)
    if np.any(w < 0):
        raise ValueError(f"PC{k} has mixed-sign weights; DOY rescaling isn't meaningful.")
    with np.errstate(all="ignore"):
        return np.asarray(D, dtype=float) @ w / w.sum()


def summarize(result: PCAResult, years: list[int] | None = None, n_show: int = 3) -> str:
    n = result.eigenvectors.shape[0]
    years = years or list(range(1, n + 1))
    lines = ["Variance explained: " + ", ".join(
        f"PC{i + 1} {v:.1%}" for i, v in enumerate(result.explained_variance_ratio[:n_show]))]
    w1 = result.weights(1)
    c1 = result.year_correlations[:, 0]
    lines.append(f"PC1 weights: {w1.min():.3f} to {w1.max():.3f}")
    lines.append(f"PC1 corr with each year: {c1.min():.2f} to {c1.max():.2f} "
                 f"(weakest: {years[int(c1.argmin())]})")
    return "\n".join(lines)
