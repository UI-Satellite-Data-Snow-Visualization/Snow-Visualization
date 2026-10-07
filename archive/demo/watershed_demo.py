"""Mask a real watershed onto the MODIS 500 m grid, then run the PCA pipeline on it.

    python watershed_demo.py                         # South Fork Boise (HUC8 17050113)
    python watershed_demo.py --geojson other.geojson --all-touched

The boundary is real (USGS WBD). The FDL values inside it are still synthetic,
so the PC1 map shows the dummy pattern, not real snowmelt.
Writes output/pc1_<id>.tif (MODIS sinusoidal GeoTIFF) and output/watershed_demo.png.
"""
import argparse
from pathlib import Path

import numpy as np

from snowpca import build_matrix, make_dummy_fdl_stack, run_pca, summarize, to_raster
from snowpca import watershed as ws

HERE = Path(__file__).parent
DEFAULT_GEOJSON = HERE / "data" / "wbd_huc8_17050113.geojson"
MIN_VALID_FRAC = 0.9


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--geojson", type=Path, default=DEFAULT_GEOJSON)
    ap.add_argument("--years", type=int, default=17)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--all-touched", action="store_true", help="include every pixel the boundary touches")
    args = ap.parse_args()

    boundary = ws.load_boundary(args.geojson)
    props = boundary.properties
    label = props.get("huc8") or props.get("huc10") or props.get("huc12") or args.geojson.stem
    print(f"Watershed: {props.get('name', '?')} ({label}), states {props.get('states', '?')}, "
          f"WBD area {props.get('areasqkm', float('nan')):,.0f} km2")

    # 1. Reproject the boundary (not the raster) and snap a grid to the MODIS pixel lattice.
    sinu = ws.to_sinusoidal(boundary.geometries)
    grid = ws.grid_for(sinu)
    mask = ws.rasterize_mask(sinu, grid, all_touched=args.all_touched)
    other = ws.rasterize_mask(sinu, grid, all_touched=not args.all_touched)
    px_km2 = ws.PIXEL_SIZE_500M ** 2 / 1e6
    rule = "all touched" if args.all_touched else "pixel center inside"
    print(f"Grid: {grid.shape[0]} x {grid.shape[1]} pixels of {ws.PIXEL_SIZE_500M:.2f} m, "
          f"origin ({grid.transform.c:.1f}, {grid.transform.f:.1f}) m sinusoidal")
    print(f"Mask ({rule}): {mask.sum():,} pixels = {mask.sum() * px_km2:,.0f} km2 "
          f"(other rule: {other.sum():,} pixels, {abs(int(other.sum()) - int(mask.sum())):,} differ)")
    print(f"MODIS tiles needed: {', '.join(ws.modis_tiles(mask, grid))}")

    # 2. Synthetic FDL years on that exact grid and mask, then the usual pipeline.
    stack = make_dummy_fdl_stack(n_years=args.years, seed=args.seed, mask=mask)
    D, index = build_matrix(stack.rasters, min_valid_frac=MIN_VALID_FRAC)
    result = run_pca(D)
    pc1 = to_raster(result.pc(1), index)
    ok = np.isfinite(pc1) & np.isfinite(stack.true_pattern)
    print(f"D matrix: {D.shape[0]:,} pixels x {D.shape[1]} years")
    print(summarize(result, stack.years))
    print(f"PC1 vs. true pattern correlation: {np.corrcoef(pc1[ok], stack.true_pattern[ok])[0, 1]:.3f}")

    # 3. Georeferenced export, then read it back to confirm the georeferencing survived.
    out = HERE / "output"
    out.mkdir(exist_ok=True)
    tif = out / f"pc1_{label}.tif"
    ws.write_geotiff(tif, pc1, grid)
    import rasterio
    with rasterio.open(tif) as src:
        same = src.crs == grid.crs and src.transform.almost_equals(grid.transform) and src.shape == grid.shape
        back = src.read(1)
    assert same and np.array_equal(np.isfinite(back), np.isfinite(pc1)), "GeoTIFF round trip failed"
    print(f"Wrote {tif.relative_to(HERE)} (CRS, transform and mask verified on read-back)")

    save_figure(sinu, grid, mask, pc1, props.get("name", label), out / "watershed_demo.png")


def save_figure(sinu, grid, mask, pc1, title, path, subtitle="synthetic FDL; dark = early"):
    try:
        import matplotlib
    except ImportError:
        print("matplotlib not installed; skipping figure.")
        return
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from rasterio.warp import calculate_default_transform, reproject, transform_geom
    from rasterio.enums import Resampling

    # Left: the native MODIS sinusoidal grid the pipeline works on. At Idaho's
    # longitude its meridians lean ~54 degrees, so shapes look sheared.
    inv = ~grid.transform
    fig, ax = plt.subplots(1, 2, figsize=(13, 6))
    ax[0].imshow(mask, cmap="Blues", interpolation="nearest")
    ax[0].set_title(f"{title}: mask on native MODIS sinusoidal grid\n(sheared; this is what the pipeline uses)")
    for g in sinu:
        for ring in ws._rings(g):
            c, r = inv * np.asarray(ring).T
            ax[0].plot(c - 0.5, r - 0.5, color="tab:red", lw=0.8)

    # Right: PC1 reprojected to Web Mercator for display only, the way a web map
    # would show it. Nearest neighbor, so no values are blended. Export stays native.
    h, w = grid.shape
    left, top = grid.transform * (0, 0)
    right, bottom = grid.transform * (w, h)
    dst_t, dw, dh = calculate_default_transform(grid.crs, "EPSG:3857", w, h, left, bottom, right, top)
    shown = np.full((dh, dw), np.nan, dtype="float32")
    reproject(pc1.astype("float32"), shown, src_transform=grid.transform, src_crs=grid.crs, src_nodata=np.nan,
              dst_transform=dst_t, dst_crs="EPSG:3857", dst_nodata=np.nan, resampling=Resampling.nearest)
    rows, cols = np.nonzero(np.isfinite(shown))   # crop the empty corners of the sheared grid
    r0, c0 = max(rows.min() - 5, 0), max(cols.min() - 5, 0)
    r1, c1 = rows.max() + 6, cols.max() + 6
    shown = shown[r0:r1, c0:c1]
    dst_t = dst_t * dst_t.translation(c0, r0)
    im = ax[1].imshow(shown, cmap="gray")
    ax[1].set_title(f"PC1 in Web Mercator, display only\n({subtitle})")
    fig.colorbar(im, ax=ax[1], fraction=0.046)
    inv_wm = ~dst_t
    for g in sinu:
        for ring in ws._rings(transform_geom(grid.crs, "EPSG:3857", g)):
            c, r = inv_wm * np.asarray(ring).T
            ax[1].plot(c - 0.5, r - 0.5, color="tab:red", lw=0.8)
    for a in ax:
        a.set_xticks([]); a.set_yticks([])
    fig.tight_layout(); fig.savefig(path, dpi=110)
    print(f"Saved {path.name}")


if __name__ == "__main__":
    main()
