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
from watershed_demo import save_figure                              # noqa: E402

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
    save_figure(sinu, grid, mask, pc1, props.get("name", label), out / "real_pc1.png",
                subtitle=f"MOD10A1F, {years[0]}-{years[-1]}, NDSI >= {args.threshold:g}; dark = early")


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


def write_int16(path, array, grid):
    import rasterio
    with rasterio.open(path, "w", driver="GTiff", height=grid.shape[0], width=grid.shape[1], count=1,
                       dtype="int16", crs=grid.crs, transform=grid.transform, nodata=F.NODATA,
                       compress="deflate") as dst:
        dst.write(array, 1)


if __name__ == "__main__":
    main()
