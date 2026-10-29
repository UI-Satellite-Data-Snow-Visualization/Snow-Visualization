"""Compare team FDL, computed from daily MOD10A1F files, with Woodruff's FDL mosaics.

Run from api/:
    python -m jobs.compare_woodruff_fdl --years 2016
    python -m jobs.compare_woodruff_fdl --years 2000-2016 --download --delete-raw
Needs MOD10A1F for h09v04 and h10v04 in db/raw/ (or --download fetches it;
--delete-raw then removes the files it fetched once that year is compared) and
Woodruff's reference files. --reference takes his original ZIP or a folder holding them
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
Per year: compare_<year>.json, diff_<year>.png and team_fdl_<year>.tif (variant A,
cropped to the watershed). With 3+ years of team_fdl_*.tif, it also runs the same
PCA on team and Woodruff FDLs and compares PC1 (pca_compare.json/.png), and
writes summary.json. All in output/woodruff_fdl/ (gitignored).
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
    ap.add_argument("--years", "--year", type=year_list, required=True, help="e.g. 2016, 2000-2016 or 2001,2005")
    ap.add_argument("--reference", type=Path, default=DB_DIR / "validation" / "woodruff" / "source")
    ap.add_argument("--downloads", type=Path, default=RAW_DIR)
    ap.add_argument("--download", action="store_true", help="fetch missing daily files from NSIDC first")
    ap.add_argument("--delete-raw", action="store_true", help="delete files fetched by this run once compared")
    ap.add_argument("--threshold", type=float, default=10)
    ap.add_argument("--out", type=Path, default=HERE / "output" / "woodruff_fdl")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    read, source = reference_reader(args.reference)
    print(f"Reference: {source}")
    ref_grid, mask = reference_mask(read, args.years[0])
    print(f"Watershed: {mask.sum():,} pixels")
    if args.download:
        from jobs.download import fetch_year, login
        login()

    for year in args.years:
        fetched = []
        if args.download:
            for tile in TILES:
                fetched += fetch_year(year, tile, out=args.downloads)
        try:
            compare_year(year, read, ref_grid, mask, args)
        finally:
            if args.delete_raw:
                for f in fetched:
                    f.unlink(missing_ok=True)

    summarize_years(args.out)
    pca_compare(read, ref_grid, mask, args.out)


def year_list(text):
    years = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        years += range(int(a), int(b or a) + 1)
    return years


def reference_mask(read, year):
    """Grid of the reference mosaic and the watershed mask on it (pixel center inside)."""
    with MemoryFile(read(f"FDL_NDSI10/MOSAIC/FDL{year}_m.tif")) as mem, mem.open() as src:
        grid = (src.shape, src.crs, src.transform)
    b = "Watershed_boundary/Watershed"
    reader = shapefile.Reader(shp=io.BytesIO(read(b + ".shp")), shx=io.BytesIO(read(b + ".shx")),
                              dbf=io.BytesIO(read(b + ".dbf")))
    prj = read(b + ".prj").decode()
    shapes = [transform_geom(prj, grid[1], s.__geo_interface__) for s in reader.shapes()]
    return grid, geometry_mask(shapes, grid[0], grid[2], invert=True)


def read_reference(read, year, ref_grid):
    with MemoryFile(read(f"FDL_NDSI10/MOSAIC/FDL{year}_m.tif")) as mem, mem.open() as src:
        if (src.shape, src.crs, src.transform) != ref_grid:
            raise ValueError(f"Reference FDL{year} is on a different grid")
        return src.read(1).astype(np.int32)


def compare_year(year, read, ref_grid, mask, args):
    ref = read_reference(read, year, ref_grid)
    shape, crs, transform = ref_grid
    rows, cols = np.nonzero(mask)
    r0, r1 = int(rows.min()), int(rows.max()) + 1
    print(f"Year {year}")

    ours = {k: np.full(shape, F.NODATA, dtype=np.int16) for k in VARIANTS}
    for i, tile in enumerate(TILES):
        files = sorted(args.downloads.glob(f"MOD10A1F.A{year}*.{tile}.*.hdf"), key=F.doy_of)
        if not files:
            raise SystemExit(f"No {year} files for {tile} in {args.downloads}; run jobs.download or pass --download.")
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

    report = {"year": year, "threshold": args.threshold, "watershed_pixels": int(mask.sum()),
              "reference_codes": code_counts(ref[mask]), "variants": {}}
    for key, (layer, start) in VARIANTS.items():
        stats = compare(ours[key][mask].astype(np.int32), ref[mask])
        stats.update(layer=layer, start_doy=start, codes=code_counts(ours[key][mask]))
        report["variants"][key] = stats
        print(f"  {key} ({layer}, start DOY {start}): {stats['compared']:,} px; exact {stats['exact']:.1%}, "
              f"within 3 d {stats['within_3']:.1%}, within 7 d {stats['within_7']:.1%}; "
              f"bias {stats['mean_diff']:+.1f} d, MAE {stats['mae']:.1f} d, r {stats['pearson']:.3f}; "
              f"code class agreement {stats['class_agreement']:.2%}")
    (args.out / f"compare_{year}.json").write_text(json.dumps(report, indent=2))
    save_team_fdl(args.out / f"team_fdl_{year}.tif", ours["A"], mask, ref_grid, year)
    save_figure(ref, ours["A"], mask, (r0, r1), year, "A", VARIANTS["A"], args.out / f"diff_{year}.png")


def crop_of(mask):
    rows, cols = np.nonzero(mask)
    return slice(int(rows.min()), int(rows.max()) + 1), slice(int(cols.min()), int(cols.max()) + 1)


def save_team_fdl(path, fdl, mask, ref_grid, year):
    """Variant A, cropped to the watershed's bounding box, -1 outside the watershed."""
    _, crs, transform = ref_grid
    rs, cs = crop_of(mask)
    data = np.where(mask[rs, cs], fdl[rs, cs], F.NODATA).astype(np.int16)
    with rasterio.open(path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1], count=1,
                       dtype="int16", crs=crs, transform=transform * transform.translation(cs.start, rs.start),
                       nodata=F.NODATA, compress="deflate") as dst:
        dst.write(data, 1)
        dst.update_tags(year=str(year), method="snow/fdl.py fdl_lds, CGF_NDSI_Snow_Cover, start DOY 91",
                        codes="0 = never snow, 365 = never melted, -1 = no data or outside watershed")


def summarize_years(out):
    reports = sorted((json.loads(p.read_text()) for p in out.glob("compare_*.json")), key=lambda r: r["year"])
    if not reports:
        return
    rows = []
    print("\nYear   A exact  A within 3 d  A bias  A class agree   B exact  C exact")
    for r in reports:
        v = r["variants"]
        rows.append({"year": r["year"], **{f"{k}_{m}": v[k][m] for k in v
                     for m in ("exact", "within_3", "within_7", "mean_diff", "mae", "pearson", "class_agreement")}})
        print(f"{r['year']}   {v['A']['exact']:6.1%}   {v['A']['within_3']:10.1%}   {v['A']['mean_diff']:+5.1f}"
              f"   {v['A']['class_agreement']:11.2%}   {v['B']['exact']:6.1%}   {v['C']['exact']:6.1%}")
    tot = {k: sum(r["variants"][k]["compared"] for r in reports) for k in VARIANTS}
    pooled = {k: sum(r["variants"][k]["exact"] * r["variants"][k]["compared"] for r in reports) / tot[k]
              for k in VARIANTS}
    print("Pooled exact match: " + ", ".join(f"{k} {pooled[k]:.2%}" for k in VARIANTS))
    (out / "summary.json").write_text(json.dumps({"years": rows, "pooled_exact": pooled}, indent=2))


def pca_compare(read, ref_grid, mask, out):
    """Same PCA on team (variant A) and Woodruff FDLs over the same pixels; compare PC1."""
    from snow.matrix import build_matrix, to_raster
    from snow.pca import run_pca

    years = sorted(int(p.stem.split("_")[-1]) for p in out.glob("team_fdl_*.tif"))
    if len(years) < 3:
        return
    rs, cs = crop_of(mask)
    m = mask[rs, cs]
    team, ref = [], []
    for y in years:
        with rasterio.open(out / f"team_fdl_{y}.tif") as src:
            team.append(src.read(1).astype(float))
        ref.append(read_reference(read, y, ref_grid)[rs, cs].astype(float))
    # One pixel set for both: a real melt date (1-364) in every year in both datasets.
    keep = m.copy()
    for t, r in zip(team, ref):
        keep &= (t > 0) & (t < 365) & (r > 0) & (r < 365)
    team = [np.where(keep, t, np.nan) for t in team]
    ref = [np.where(keep, r, np.nan) for r in ref]
    Dt, it = build_matrix(team)
    Dr, ir = build_matrix(ref)
    assert np.array_equal(it.flat_idx, ir.flat_idx)

    from scipy.stats import spearmanr
    report = {"years": years, "pixels": int(len(Dt)), "watershed_pixels": int(m.sum())}
    for label, corr in (("covariance", False), ("correlation", True)):
        a, b = run_pca(Dt, use_correlation=corr), run_pca(Dr, use_correlation=corr)
        report[label] = {
            "team_pc1_variance": float(a.explained_variance_ratio[0]),
            "woodruff_pc1_variance": float(b.explained_variance_ratio[0]),
            "pc1_pearson": float(np.corrcoef(a.pc(1), b.pc(1))[0, 1]),
            "pc1_spearman": float(spearmanr(a.pc(1), b.pc(1)).statistic),
            "max_weight_difference": float(np.max(np.abs(a.weights() - b.weights()))),
            "team_weights": a.weights().tolist(), "woodruff_weights": b.weights().tolist(),
        }
        r = report[label]
        print(f"PCA ({label}), {len(years)} years, {len(Dt):,} pixels: PC1 variance team {r['team_pc1_variance']:.2%} "
              f"vs Woodruff {r['woodruff_pc1_variance']:.2%}; PC1 r = {r['pc1_pearson']:.4f}, "
              f"Spearman {r['pc1_spearman']:.4f}; max year-weight difference {r['max_weight_difference']:.4f}")
        if label == "covariance":
            pc_team, pc_ref = to_raster(a.pc(1), it), to_raster(b.pc(1), ir)
    (out / "pca_compare.json").write_text(json.dumps(report, indent=2))
    save_pca_figure(pc_team, pc_ref, years, out / "pca_compare.png")


def save_pca_figure(pc_team, pc_ref, years, path):
    try:
        import matplotlib
    except ImportError:
        return
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

    seq = LinearSegmentedColormap.from_list("melt", ["#0d366b", "#256abf", "#6da7ec", "#cde2fb"])
    div = LinearSegmentedColormap.from_list("div", ["#1c5cab", "#86b6ef", "#f0efec", "#f2a28a", "#b8371b"])
    seq.set_bad("white"); div.set_bad("white")
    lo, hi = np.nanpercentile(np.r_[pc_team[np.isfinite(pc_team)], pc_ref[np.isfinite(pc_ref)]], [2, 98])
    fig, ax = plt.subplots(1, 3, figsize=(16, 5.2))
    for x, data, title in ((ax[0], pc_ref, "PC1 from Woodruff's FDL"), (ax[1], pc_team, "PC1 from team FDL")):
        im = x.imshow(data, cmap=seq, vmin=lo, vmax=hi, interpolation="nearest")
        x.set_title(title, loc="left")
    cb = fig.colorbar(im, ax=ax[:2], fraction=0.025, pad=0.01, ticks=[lo, hi])
    cb.ax.set_yticklabels(["earlier", "later"])
    d = pc_team - pc_ref
    lim = max(1.0, float(np.nanpercentile(np.abs(d), 99)))
    im = ax[2].imshow(d, cmap=div, norm=TwoSlopeNorm(0, -lim, lim), interpolation="nearest")
    ax[2].set_title("Team minus Woodruff (PC1 units)", loc="left")
    fig.colorbar(im, ax=ax[2], fraction=0.046, pad=0.02, extend="both")
    for x in ax:
        x.set_xticks([]); x.set_yticks([])
    fig.suptitle(f"Covariance PCA, {years[0]}-{years[-1]} ({len(years)} years); native MODIS grid (sheared)",
                 fontsize=10, color="#6b6a66")
    fig.savefig(path, dpi=100, bbox_inches="tight", facecolor="white")
    plt.close(fig)


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


def code_class(a):
    """0 never snow, 1 melt date, 2 never melted (365/366), 3 no data."""
    return np.select([a == 0, (a > 0) & (a < 365), (a == 365) | (a == 366)], [0, 1, 2], 3)


def compare(ours, ref):
    """Melt-date agreement where both have a date (1-364), plus agreement on the special codes."""
    ok = (ours > 0) & (ours < 365) & (ref > 0) & (ref < 365)
    d = ours[ok] - ref[ok]
    co, cr = code_class(ours), code_class(ref)
    return {"compared": int(ok.sum()), "class_agreement": float(np.mean(co == cr)),
            "class_confusion": {f"ours{a}_ref{b}": int(((co == a) & (cr == b)).sum())
                                for a in range(4) for b in range(4) if a != b and ((co == a) & (cr == b)).any()}, "exact": float(np.mean(d == 0)),
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
