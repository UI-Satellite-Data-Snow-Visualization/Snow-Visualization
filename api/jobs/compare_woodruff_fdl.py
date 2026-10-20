"""Compare team FDL, computed from daily MOD10A1F files, with Woodruff's FDL mosaics.

Run from api/: python -m jobs.compare_woodruff_fdl --year 2016
Needs MOD10A1F for h09v04 and h10v04 in db/raw/ (jobs.download) and Woodruff's
reference files. --reference takes his original ZIP or a folder holding them
unzipped (FDL_NDSI10/ and Watershed_boundary/). The default,
db/validation/woodruff/source/, works with either: unzipped folders if present,
otherwise the one ZIP there (the layout Collect-WoodruffValidation.ps1 builds).

Woodruff's mosaic is h09v04 + h10v04 side by side on the native MODIS grid, so
the comparison is pixel for pixel with no resampling. The history behind his
rasters is unconfirmed, so several FDL variants are computed from the same files:
  A  CGF layer, DOY 91 two-way search (the current starter script)
  B  cloud-containing layer (MOD10A1_NDSI_Snow_Cover), DOY 91 two-way search
  C  cloud-containing layer, forward search from DOY 1
  D  CGF layer, forward search from DOY 1
Writes output/woodruff_fdl/compare_<year>.json and diff_<year>.png (gitignored).
"""
import argparse
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio
import shapefile
from rasterio.features import geometry_mask
from rasterio.io import MemoryFile
from rasterio.warp import transform_geom

from config import DB_DIR, RAW_DIR
from snow import fdl as F

HERE = Path(__file__).resolve().parent.parent   # api/
TILES = ["h09v04", "h10v04"]                       # left and right halves of the mosaic
VARIANTS = {
    "A": ("CGF_NDSI_Snow_Cover", 91),
    "B": ("MOD10A1_NDSI_Snow_Cover", 91),
    "C": ("MOD10A1_NDSI_Snow_Cover", 1),
    "D": ("CGF_NDSI_Snow_Cover", 1),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--reference", type=Path, default=DB_DIR / "validation" / "woodruff" / "source")
    ap.add_argument("--downloads", type=Path, default=RAW_DIR)
    ap.add_argument("--threshold", type=float, default=10)
    ap.add_argument("--out", type=Path, default=HERE / "output" / "woodruff_fdl")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    read, source = reference_reader(args.reference)
    print(f"Reference: {source}")
    with MemoryFile(read(f"FDL_NDSI10/MOSAIC/FDL{args.year}_m.tif")) as mem, mem.open() as src:
        ref, crs, transform = src.read(1).astype(np.int32), src.crs, src.transform
    b = "Watershed_boundary/Watershed"
    reader = shapefile.Reader(shp=io.BytesIO(read(b + ".shp")), shx=io.BytesIO(read(b + ".shx")),
                              dbf=io.BytesIO(read(b + ".dbf")))
    prj = read(b + ".prj").decode()
    shapes = [transform_geom(prj, crs, s.__geo_interface__) for s in reader.shapes()]
    mask = geometry_mask(shapes, ref.shape, transform, invert=True)
    rows, cols = np.nonzero(mask)
    r0, r1 = int(rows.min()), int(rows.max()) + 1
    print(f"Reference FDL {args.year}: {ref.shape}, watershed {mask.sum():,} pixels, rows {r0}-{r1}")

    ours = {k: np.full(ref.shape, F.NODATA, dtype=np.int16) for k in VARIANTS}
    for i, tile in enumerate(TILES):
        files = sorted(args.downloads.glob(f"MOD10A1F.A{args.year}*.{tile}.*.hdf"), key=F.doy_of)
        if not files:
            raise SystemExit(f"No {args.year} files for {tile} in {args.downloads}; run jobs.download first.")
        tt = F.tile_transform(files[0])
        if not np.allclose([tt.c, tt.f], transform * (2400 * i, 0), atol=1e-3):
            raise ValueError(f"{tile} is not at mosaic column {2400 * i}")
        tile_cols = cols[(cols >= 2400 * i) & (cols < 2400 * (i + 1))] - 2400 * i
        if tile_cols.size == 0:
            continue
        c0, c1 = int(tile_cols.min()), int(tile_cols.max()) + 1
        window = (slice(r0, r1), slice(c0, c1))
        for layer in {v[0] for v in VARIANTS.values()}:
            doys, stack = read_layer(files, layer, window)
            for key, (lay, start) in VARIANTS.items():
                if lay == layer:
                    fdl, _ = F.fdl_lds(stack, doys, args.threshold, start)
                    ours[key][r0:r1, 2400 * i + c0:2400 * i + c1] = fdl
            del stack
        print(f"  {tile}: {len(files)} days (DOY {doys[0]}-{doys[-1]})")

    report = {"year": args.year, "threshold": args.threshold, "watershed_pixels": int(mask.sum()),
              "reference_codes": code_counts(ref[mask]), "variants": {}}
    for key, (layer, start) in VARIANTS.items():
        stats = compare(ours[key][mask].astype(np.int32), ref[mask])
        stats.update(layer=layer, start_doy=start, codes=code_counts(ours[key][mask]))
        report["variants"][key] = stats
        print(f"{key} ({layer}, start DOY {start}): {stats['compared']:,} px; exact {stats['exact']:.1%}, "
              f"within 3 d {stats['within_3']:.1%}, within 7 d {stats['within_7']:.1%}; "
              f"bias {stats['mean_diff']:+.1f} d, MAE {stats['mae']:.1f} d, r {stats['pearson']:.3f}")
    (args.out / f"compare_{args.year}.json").write_text(json.dumps(report, indent=2))
    best = max(report["variants"], key=lambda k: report["variants"][k]["within_3"])
    save_figure(ref, ours[best], mask, (r0, r1), args.year, best, VARIANTS[best], args.out / f"diff_{args.year}.png")
    print(f"Wrote {args.out / f'compare_{args.year}.json'} and diff_{args.year}.png (variant {best})")


def reference_reader(path: Path):
    """A function that returns a reference file's bytes, from a ZIP or a folder."""
    if path.is_dir() and not (path / "FDL_NDSI10").is_dir():
        zips = sorted(path.glob("*.zip"))
        if len(zips) != 1:
            raise SystemExit(f"{path} has neither unzipped FDL_NDSI10/ nor exactly one ZIP; pass --reference.")
        path = zips[0]
    if path.is_dir():
        return (lambda rel: (path / rel).read_bytes()), path
    z = zipfile.ZipFile(path)
    return z.read, path


def read_layer(files, layer, window):
    """One named layer, raw uint8 codes, for a window of each daily file."""
    from pyhdf.SD import SD, SDC

    rows, cols = window
    arrays = [np.asarray(SD(str(f), SDC.READ).select(layer)[rows, cols], dtype=np.uint8) for f in files]
    return np.array([F.doy_of(f) for f in files]), np.stack(arrays)


def code_counts(a):
    return {"0": int((a == 0).sum()), "365": int((a == 365).sum()), "366": int((a == 366).sum()),
            "-1": int((a == -1).sum())}


def compare(ours, ref):
    """Agreement where both have a real melt date (1-364)."""
    ok = (ours > 0) & (ours < 365) & (ref > 0) & (ref < 365)
    d = ours[ok] - ref[ok]
    return {"compared": int(ok.sum()), "exact": float(np.mean(d == 0)),
            "within_1": float(np.mean(np.abs(d) <= 1)), "within_3": float(np.mean(np.abs(d) <= 3)),
            "within_7": float(np.mean(np.abs(d) <= 7)), "mean_diff": float(d.mean()),
            "median_diff": float(np.median(d)), "mae": float(np.abs(d).mean()),
            "pearson": float(np.corrcoef(ours[ok], ref[ok])[0, 1])}


def save_figure(ref, ours, mask, rows, year, key, variant, path):
    try:
        import matplotlib
    except ImportError:
        return
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

    r0, r1 = rows
    cols = np.nonzero(mask.any(axis=0))[0]
    sl = (slice(r0, r1), slice(cols.min(), cols.max() + 1))
    m = mask[sl]
    a = np.where(m & (ref[sl] > 0) & (ref[sl] < 365), ref[sl], np.nan).astype(float)
    b = np.where(m & (ours[sl] > 0) & (ours[sl] < 365), ours[sl], np.nan).astype(float)
    seq = LinearSegmentedColormap.from_list("melt", ["#0d366b", "#256abf", "#6da7ec", "#cde2fb"])
    div = LinearSegmentedColormap.from_list("div", ["#1c5cab", "#86b6ef", "#f0efec", "#f2a28a", "#b8371b"])
    seq.set_bad("white"); div.set_bad("white")
    lo, hi = np.nanpercentile(np.r_[a[np.isfinite(a)], b[np.isfinite(b)]], [2, 98])
    fig, ax = plt.subplots(1, 3, figsize=(16, 5.2))
    for x, data, title in ((ax[0], a, f"Woodruff FDL {year}"), (ax[1], b, f"Team FDL {year}, variant {key}")):
        im = x.imshow(data, cmap=seq, vmin=lo, vmax=hi, interpolation="nearest")
        x.set_title(title, loc="left")
    fig.colorbar(im, ax=ax[:2], fraction=0.025, pad=0.01, label="Day of year (dark = earlier)")
    im = ax[2].imshow(b - a, cmap=div, norm=TwoSlopeNorm(0, -30, 30), interpolation="nearest")
    ax[2].set_title("Team minus Woodruff (days)", loc="left")
    fig.colorbar(im, ax=ax[2], fraction=0.046, pad=0.02, extend="both")
    for x in ax:
        x.set_xticks([]); x.set_yticks([])
    fig.suptitle(f"{variant[0]}, start DOY {variant[1]}; native MODIS grid (sheared)", fontsize=10, color="#6b6a66")
    fig.savefig(path, dpi=100, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
