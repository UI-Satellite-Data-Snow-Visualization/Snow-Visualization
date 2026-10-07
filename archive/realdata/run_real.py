"""Real MOD10A1F in, PC1 map and GeoTIFF out, for one watershed.

    python run_real.py --years 2020 2021 2022 2023 2024
    python run_real.py --years 2020 2021 2022 --geojson ../demo/data/wbd_huc8_17050113.geojson

Steps: watershed mask on the MODIS grid -> read that window from each daily
file -> FDL per year (fdl.py) -> drop 0 / 365 / no-data -> D matrix -> PCA.
Writes output/fdl_<id>_<year>.tif, output/pc1_<id>.tif and output/real_pc1.png.
Run download.py first. Uses the venv in ../demo.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "demo"))

from snowpca import build_matrix, run_pca, summarize, to_raster   # noqa: E402
from snowpca import watershed as ws                                 # noqa: E402

import fdl as F                                                     # noqa: E402

DEFAULT_GEOJSON = HERE.parent / "demo" / "data" / "wbd_huc8_17050113.geojson"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--years", type=int, nargs="+", required=True)
    ap.add_argument("--geojson", type=Path, default=DEFAULT_GEOJSON)
    ap.add_argument("--threshold", type=float, default=10)
    ap.add_argument("--start-doy", type=int, default=91)
    ap.add_argument("--downloads", type=Path, default=HERE / "downloads")
    ap.add_argument("--correlation", action="store_true", help="correlation PCA instead of covariance (D06)")
    args = ap.parse_args()

    boundary = ws.load_boundary(args.geojson)
    props = boundary.properties
    label = props.get("huc8") or props.get("huc10") or props.get("huc12") or args.geojson.stem
    sinu = ws.to_sinusoidal(boundary.geometries)
    grid = ws.grid_for(sinu)
    mask = ws.rasterize_mask(sinu, grid)
    tiles = ws.modis_tiles(mask, grid)
    if len(tiles) != 1:
        sys.exit(f"Watershed spans tiles {tiles}; tile stitching isn't built yet.")
    tile = tiles[0]
    print(f"Watershed: {props.get('name', '?')} ({label}), {mask.sum():,} pixels, tile {tile}")

    out = HERE / "output"
    out.mkdir(exist_ok=True)
    rasters, years = [], []
    for year in args.years:
        files = sorted(args.downloads.glob(f"MOD10A1F.A{year}*.{tile}.*.hdf"))
        if not files:
            print(f"{year}: no files, skipped")
            continue
        window = tile_window(F.tile_transform(files[0]), grid)
        doys, stack = F.read_stack(files, window)
        fdl, _ = F.fdl_lds(stack, doys, args.threshold, args.start_doy)
        write_int16(out / f"fdl_{label}_{year}.tif", fdl, grid)

        inside = fdl[mask]
        n0, n365, nnd = (inside == F.NEVER_SNOW).sum(), (inside == F.NEVER_MELTED).sum(), (inside == F.NODATA).sum()
        ok = inside[(inside != F.NEVER_SNOW) & (inside != F.NEVER_MELTED) & (inside != F.NODATA)]
        print(f"{year}: {len(files)} days (DOY {doys[0]}-{doys[-1]}); FDL median DOY {np.median(ok):.0f} "
              f"(10-90%: {np.percentile(ok, 10):.0f}-{np.percentile(ok, 90):.0f}); "
              f"never snow {n0}, never melted {n365}, no data {nnd}")

        r = fdl.astype(float)
        r[~mask | (fdl == F.NEVER_SNOW) | (fdl == F.NEVER_MELTED) | (fdl == F.NODATA)] = np.nan
        rasters.append(r)
        years.append(year)

    D, index = build_matrix(rasters, min_valid_frac=1.0)
    result = run_pca(D, use_correlation=args.correlation)
    pc1 = to_raster(result.pc(1), index)
    print(f"D matrix: {D.shape[0]:,} pixels x {D.shape[1]} years "
          f"({'correlation' if args.correlation else 'covariance'} PCA)")
    print(summarize(result, years))
    print(f"PC1 vs. mean FDL across years: r = {np.corrcoef(result.pc(1), D.mean(axis=1))[0, 1]:.3f}")

    tif = out / f"pc1_{label}.tif"
    ws.write_geotiff(tif, pc1, grid)
    print(f"Wrote {tif.relative_to(HERE)}")
    save_figure(sinu, grid, rasters, years, pc1, result, props.get("name", label), args.threshold,
                out / "real_pc1.png")

def tile_window(tile_t, grid) -> tuple[slice, slice]:
    """Rows/cols of the tile that the watershed grid covers (both sit on the same MODIS lattice)."""
    col = (grid.transform.c - tile_t.c) / tile_t.a
    row = (grid.transform.f - tile_t.f) / tile_t.e
    c0, r0 = round(col), round(row)
    if abs(col - c0) > 1e-3 or abs(row - r0) > 1e-3:
        raise ValueError("Watershed grid is not aligned to the tile's pixels.")
    h, w = grid.shape
    if r0 < 0 or c0 < 0 or r0 + h > 2400 or c0 + w > 2400:
        raise ValueError("Watershed grid extends past the tile edge; needs stitching.")
    return slice(r0, r0 + h), slice(c0, c0 + w)


# Blue ramp (dataviz reference palette), dark = early melt, light = late.
RAMP = ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"]
INK, MUTED, GRID = "#1f1f1d", "#6b6a66", "#e4e3df"


def save_figure(sinu, grid, fdl_maps, years, pc1, result, name, threshold, path):
    """PC1 map + variance explained on top; each year's FDL below on one shared date scale."""
    try:
        import matplotlib
    except ImportError:
        print("matplotlib not installed; skipping figure.")
        return
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from datetime import date, timedelta
    from matplotlib.colors import LinearSegmentedColormap
    from rasterio.enums import Resampling
    from rasterio.warp import calculate_default_transform, reproject, transform_geom

    cmap = LinearSegmentedColormap.from_list("melt", RAMP)
    cmap.set_bad("white")

    # Web Mercator for display only (nearest neighbor); computation stays on the MODIS grid.
    h, w = grid.shape
    left, top = grid.transform * (0, 0)
    right, bottom = grid.transform * (w, h)
    dst_t, dw, dh = calculate_default_transform(grid.crs, "EPSG:3857", w, h, left, bottom, right, top)

    def show(a):
        o = np.full((dh, dw), np.nan, dtype="float32")
        reproject(a.astype("float32"), o, src_transform=grid.transform, src_crs=grid.crs, src_nodata=np.nan,
                  dst_transform=dst_t, dst_crs="EPSG:3857", dst_nodata=np.nan, resampling=Resampling.nearest)
        return o

    shown_pc1 = show(pc1)
    rows, cols = np.nonzero(np.isfinite(shown_pc1))
    r0, c0 = max(rows.min() - 4, 0), max(cols.min() - 4, 0)
    r1, c1 = rows.max() + 5, cols.max() + 5
    crop_t = dst_t * dst_t.translation(c0, r0)
    outline = [ws._rings(transform_geom(grid.crs, "EPSG:3857", g)) for g in sinu]
    outline = [np.asarray(ring).T for rings in outline for ring in rings]

    def draw(ax, a, **kw):
        im = ax.imshow(a[r0:r1, c0:c1], cmap=cmap, interpolation="nearest", **kw)
        inv = ~crop_t
        for ring in outline:
            c, r = inv * ring
            ax.plot(c - 0.5, r - 0.5, color=MUTED, lw=0.6)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        return im

    n = len(years)
    fig = plt.figure(figsize=(max(12, 2.6 * n), 8.2))
    gs = fig.add_gridspec(2, n, height_ratios=[1.6, 1], hspace=0.12, wspace=0.08)
    top_gs = gs[0, :].subgridspec(1, 2, width_ratios=[1.6, 1], wspace=0.25)
    fig.suptitle(f"{name}: MOD10A1F {years[0]}-{years[-1]}, NDSI >= {threshold:g}", color=INK, fontsize=14)

    # PC1 map. Its units are relative, so the colorbar says early/late, not dates.
    ax = fig.add_subplot(top_gs[0])
    lo, hi = np.nanpercentile(shown_pc1, [2, 98])
    im = draw(ax, shown_pc1, vmin=lo, vmax=hi)
    ax.set_title("PC1: recurring melt pattern", color=INK, fontsize=12, loc="left")
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02, ticks=[lo, hi])
    cb.ax.set_yticklabels(["earlier", "later"], color=MUTED)
    cb.outline.set_visible(False)

    # Variance explained per component (single series, so no legend).
    ax = fig.add_subplot(top_gs[1])
    k = len(result.explained_variance_ratio)
    pct = 100 * result.explained_variance_ratio
    ax.bar(range(1, k + 1), pct, width=0.5, color=RAMP[2])
    ax.set_title("Variance explained by each component", color=INK, fontsize=12, loc="left")
    ax.set_xticks(range(1, k + 1), [f"PC{i}" for i in range(1, k + 1)])
    ax.set_ylim(0, 100); ax.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=MUTED, length=0)
    for i in range(min(2, k)):
        ax.text(i + 1, pct[i] + 2, f"{pct[i]:.1f}%", ha="center", color=INK, fontsize=10)

    # FDL per year: one shared scale so years compare directly.
    lo_d, hi_d = np.nanpercentile(np.concatenate([m[np.isfinite(m)] for m in fdl_maps]), [2, 98])
    ticks = [d for d in (32, 60, 91, 121, 152, 182, 213) if lo_d <= d <= hi_d]   # month starts (non-leap)
    axes = []
    for j, (m, y) in enumerate(zip(fdl_maps, years)):
        ax = fig.add_subplot(gs[1, j])
        im = draw(ax, show(m), vmin=lo_d, vmax=hi_d)
        ax.set_title(f"{y}  (median {_doy_label(np.nanmedian(m), y)})", color=INK, fontsize=10)
        axes.append(ax)
    cb = fig.colorbar(im, ax=axes, orientation="horizontal", ticks=ticks, fraction=0.06, pad=0.04, shrink=0.5)
    cb.ax.set_xticklabels([_doy_label(d) for d in ticks], color=MUTED)
    cb.outline.set_visible(False)
    cb.set_label("First day land (FDL), same scale for every year", color=MUTED)

    fig.savefig(path, dpi=110, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path.relative_to(HERE)}")


def _doy_label(doy, year=2021):
    from datetime import date, timedelta
    return (date(year, 1, 1) + timedelta(days=int(round(doy)) - 1)).strftime("%b %-d")


def write_int16(path, array, grid):
    import rasterio
    with rasterio.open(path, "w", driver="GTiff", height=grid.shape[0], width=grid.shape[1], count=1,
                       dtype="int16", crs=grid.crs, transform=grid.transform, nodata=F.NODATA,
                       compress="deflate") as dst:
        dst.write(array, 1)


if __name__ == "__main__":
    main()
