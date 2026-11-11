"""Check that one daily snow file reads correctly before a full precompute.

    python -m jobs.inspect_granule PATH                 (local .hdf or .h5)
    python -m jobs.inspect_granule PATH --layer NDSI_Snow_Cover
    python -m jobs.inspect_granule --fetch viirs --date 2024-04-15 --tile h09v04

Prints the layer's dtype and shape, the tile transform and whether it sits on
the product's registered grid, and a count of NDSI values and flag codes.
--fetch downloads one granule into db/raw/ (gitignored) using your Earthdata
login, then inspects it. Run from api/.
"""
import argparse
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

from config import RAW_DIR
from snow import chunks, granules, products

CODE_NAMES = {200: "missing", 201: "no decision", 211: "night", 237: "inland water",
              239: "ocean", 250: "cloud", 251: "missing data", 252: "L1B unusable",
              253: "bowtie trim", 254: "L1B fill / detector saturated", 255: "fill"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", type=Path, help="local daily file")
    ap.add_argument("--layer", help="layer name (default: the product's gap-filled NDSI layer)")
    ap.add_argument("--fetch", metavar="PRODUCT", help="download one granule of PRODUCT first (e.g. viirs)")
    ap.add_argument("--date", type=date.fromisoformat, default=date(2024, 4, 15))
    ap.add_argument("--tile", default="h09v04")
    args = ap.parse_args()
    if bool(args.path) == bool(args.fetch):
        ap.error("Give a local PATH or --fetch PRODUCT, not both")

    if args.fetch:
        product = products.get(args.fetch)
        path = fetch_one(product, args.date, args.tile)
    else:
        path = args.path
        product = products.for_file(path.name) if _registered(path.name) else None
    layer = args.layer or (product.layer if product else None)
    if layer is None:
        ap.error(f"{path.name} is not a registered product; pass --layer")
    inspect(path, layer, product)


def _registered(name):
    try:
        products.for_file(name)
        return True
    except ValueError:
        return False


def fetch_one(product, day, tile):
    import earthaccess
    from jobs.download import login

    login()
    results = earthaccess.search_data(
        short_name=product.short_name, version=product.version,
        temporal=(day.isoformat(), day.isoformat()),
        granule_name=product.granule_pattern(day.year, tile),
    )
    results = [g for g in results if any(f".{tile}." in u and u.endswith(product.extension)
                                         for u in g.data_links())]
    if not results:
        raise SystemExit(f"No {product.key} granule for {tile} on {day}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    paths = earthaccess.download(results[:1], str(RAW_DIR), show_progress=False)
    if not paths:
        raise SystemExit("Download failed")
    print(f"Downloaded {Path(paths[0]).name} to {RAW_DIR}")
    return Path(paths[0])


def inspect(path, layer, product):
    if path.suffix == ".h5":
        import h5py
        with h5py.File(path, "r") as f:
            print("2-D layers:", ", ".join(n.rsplit("/", 1)[-1] for n in granules.layer_names(f)))
    transform, data = granules.read_layer(path, layer)
    print(f"File:      {path.name}")
    print(f"Layer:     {layer}  dtype={data.dtype}  shape={data.shape}")
    print(f"Pixel:     {transform.a:.6f} m   upper-left ({transform.c:.3f}, {transform.f:.3f})")
    guessed = product is None
    if guessed:   # e.g. the non-gap-filled VNP10A1 samples: compare by grid size
        product = next((p for p in products.ALL if p.extension == path.suffix
                        and (p.tile_pixels,) * 2 == data.shape), None)
    if product:
        tile = path.name.split(".")[2]
        expected = chunks.tile_grid(tile, product.grid).transform
        same = np.allclose(tuple(transform)[:6], tuple(expected)[:6], rtol=0, atol=1e-3)
        print(f"Product:   {'(same grid as) ' if guessed else ''}{product.label}")
        print(f"Grid:      {'OK, matches' if same else 'MISMATCH with'} registered {product.key} grid for {tile}")
        if data.shape != (product.tile_pixels,) * 2:
            print(f"WARNING:   expected {product.tile_pixels} x {product.tile_pixels} pixels")
    counts = Counter(np.asarray(data).ravel().tolist())
    total = data.size
    ndsi = sum(n for code, n in counts.items() if code <= 100)
    snow10 = sum(n for code, n in counts.items() if 10 <= code <= 100)
    print(f"NDSI 0-100: {ndsi:,} px ({100 * ndsi / total:.1f}%), of which NDSI >= 10: {snow10:,}")
    for code in sorted(c for c in counts if c > 100):
        print(f"  code {code:3d} {CODE_NAMES.get(code, 'undefined'):<30} {counts[code]:>10,} px")


if __name__ == "__main__":
    main()
