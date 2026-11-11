"""Download daily snow tile-years once and write FDL/LDS to SQLite chunks.

Run from api/: python -m jobs.precompute_fdl --years 2021 2022 2023
VIIRS:         python -m jobs.precompute_fdl --product viirs --years 2021 2022 2023
Products: MOD10A1F.061 (default, "modis"), VNP10A1F.002 ("viirs", from 2012),
VJ110A1F.002 (NOAA-20, from 2018). Each is stored under its own key.
Default thresholds: 10 20 30 40 50. Use --threshold 10 for one threshold.
Daily files are verified, read into a shared uint8 stack, and deleted. Each
threshold is computed from that stack and committed atomically as FDL/LDS
200 x 200 chunks in db/fdl_store/snow.sqlite3. Completed thresholds are skipped.
"""

import argparse
import hashlib
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import earthaccess

from config import FDL_STORE_DIR
from jobs.download import login
from snow import fdl as F
from snow import chunks, products
from snow import granules as granule_io

STRIP_ROWS = (
    400  # FDL runs in row strips; pixels are independent, so results are identical
)

_hdf_lock = (
    threading.Lock()
)  # the HDF4/HDF5 libraries aren't thread-safe; downloads run in parallel, reads don't
_local = threading.local()


def parse_args():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--years", type=int, nargs="+", required=True)
    ap.add_argument(
        "--product",
        type=_product,
        default=products.DEFAULT,
        help="MOD10A1F.061 (default, alias modis), VNP10A1F.002 (alias viirs) or VJ110A1F.002",
    )
    ap.add_argument("--tiles", nargs="+", default=["h09v04"])
    ap.add_argument(
        "--threshold", type=float, default=None, help="compute one threshold"
    )
    ap.add_argument(
        "--thresholds",
        type=float,
        nargs="+",
        default=None,
        help="default: 10 20 30 40 50",
    )
    ap.add_argument("--start-doy", type=int, default=91)
    ap.add_argument(
        "--last-doy",
        type=int,
        default=243,
        help="last day of year to fetch (243 = Aug 31)",
    )
    ap.add_argument("--workers", type=int, default=8, help="parallel downloads")
    ap.add_argument("--out", type=Path, default=FDL_STORE_DIR)
    ap.add_argument(
        "--tmp",
        type=Path,
        default=None,
        help="folder for in-flight files (default: system temp)",
    )
    ap.add_argument(
        "--overwrite", action="store_true", help="recompute tile-years already in --out"
    )
    args = ap.parse_args()

    if args.threshold is not None and args.thresholds is not None:
        ap.error("Use --threshold or --thresholds, not both")
    if args.threshold is not None:
        args.thresholds = [args.threshold]
    elif args.thresholds is None:
        args.thresholds = [10, 20, 30, 40, 50]
    args.thresholds = sorted(set(args.thresholds))
    if any(not np.isfinite(t) or not 0 < t <= 100 for t in args.thresholds):
        ap.error("Thresholds must be in (0, 100]")
    if not 1 <= args.start_doy <= args.last_doy <= 365 or args.workers < 1:
        ap.error("Require 1 <= start DOY <= last DOY <= 365 and workers >= 1")
    early = [y for y in args.years if y < args.product.first_year]
    if early:
        ap.error(
            f"{args.product.key} ({args.product.platform}) starts in "
            f"{args.product.first_year}; no data for {early}"
        )
    return args


def _product(name):
    try:
        return products.get(name)
    except ValueError as err:
        raise argparse.ArgumentTypeError(str(err)) from err


def main():
    args = parse_args()
    product = args.product
    print(f"Product: {product.label}")
    login()
    args.out.mkdir(parents=True, exist_ok=True)
    for tile in args.tiles:
        for year in args.years:
            pending = [
                t
                for t in args.thresholds
                if args.overwrite
                or year
                not in chunks.stored_years(
                    chunks.database(args.out), [tile], t, product=product.key
                )
            ]
            if not pending:
                print(f"{tile} {year}: already stored, skipped")
                continue
            process_tile_year(tile, year, args, pending)


def process_tile_year(tile, year, args, thresholds):
    product = products.get(args.product)
    t0 = time.perf_counter()
    granules = find_granules(tile, year, args.last_doy, product)
    if not granules:
        print(f"{tile} {year}: no granules in the catalog, skipped")
        return
    doys = np.array(sorted(granules))
    gaps = sorted(set(range(1, args.last_doy + 1)) - set(doys.tolist()))
    print(
        f"{tile} {year}: {len(doys)} granules (DOY {doys[0]}-{doys[-1]}, {len(gaps)} missing days)"
    )

    stack, transform = download_stack(tile, year, granules, doys, args, product)
    t_pull = time.perf_counter() - t0

    for threshold in thresholds:
        fdl, lds = compute_layers(stack, doys, threshold, args.start_doy)
        tags = build_provenance(
            tile, year, threshold, args.start_doy, doys, gaps, granules, product
        )
        chunks.write_tile(
            chunks.database(args.out),
            tile,
            year,
            threshold,
            fdl,
            lds,
            transform,
            tags,
            overwrite=args.overwrite,
            product_grid=product.grid,
        )
        print(
            f"  {tile} {year} t{threshold:g}: stored FDL/LDS chunks; "
            f"download {t_pull:.0f}s, elapsed {time.perf_counter() - t0:.0f}s"
        )


def download_stack(tile, year, granules, doys, args, product=products.DEFAULT):
    """Download daily observations and check that every day uses the same grid.

    The (days, rows, cols) uint8 stack is allocated from the first file read, so
    its size follows the product: about 1.4 GB per MODIS tile-year (2400 x 2400)
    and 2.2 GB per VIIRS tile-year (3000 x 3000) for DOY 1-243.
    """
    t0 = time.perf_counter()
    stack = None
    transforms = [None] * len(doys)
    store_lock = threading.Lock()

    with tempfile.TemporaryDirectory(
        dir=args.tmp, prefix=f"{product.short_name.lower()}_{tile}_{year}_"
    ) as tmp:

        def work(i, doy):
            nonlocal stack
            g = granules[doy]
            path = Path(tmp) / g["name"]
            fetch(g, path)
            try:
                transform, data = read_cgf(path, product)
            finally:
                path.unlink(missing_ok=True)
            with store_lock:
                if stack is None:
                    stack = np.empty((len(doys), *data.shape), dtype=np.uint8)
                elif data.shape != stack.shape[1:]:
                    raise ValueError(f"{g['name']}: shape {data.shape} != {stack.shape[1:]}")
                transforms[i], stack[i] = transform, data

        ex = ThreadPoolExecutor(args.workers)
        try:
            futures = [ex.submit(work, i, int(d)) for i, d in enumerate(doys)]
            for n, fut in enumerate(as_completed(futures), 1):
                fut.result()  # any failure (after retries) aborts this tile-year
                if n % 50 == 0 or n == len(futures):
                    print(
                        f"  {n}/{len(futures)} files ({time.perf_counter() - t0:.0f} s)"
                    )
        except BaseException:
            ex.shutdown(wait=True, cancel_futures=True)
            raise
        ex.shutdown()
    # Every day must sit on the same grid before stacking.
    if len(set(transforms)) != 1:
        raise ValueError(
            f"{tile} {year}: daily files don't share one grid: {set(transforms)}"
        )
    return stack, transforms[0]


def compute_layers(stack, doys, threshold, start_doy):
    """Compute annual dates in row strips to bound temporary memory usage."""
    fdl = np.empty(stack.shape[1:], dtype=np.int16)
    lds = np.empty_like(fdl)
    for row in range(0, fdl.shape[0], STRIP_ROWS):
        strip = slice(row, row + STRIP_ROWS)
        fdl[strip], lds[strip] = F.fdl_lds(stack[:, strip], doys, threshold, start_doy)
    return fdl, lds


def build_provenance(
    tile, year, threshold, start_doy, doys, gaps, granules, product=products.DEFAULT
):
    tags = {
        "product": f"{product.short_name} v{product.version} (NSIDC), layer {product.layer}",
        "product_key": product.key,
        "sensor": f"{product.sensor} {product.platform}",
        "tile": tile,
        "year": str(year),
        "threshold": f"snow = NDSI {threshold:g}-100; clear = NDSI < {threshold:g} or {F.INLAND_WATER}; "
        f"missing = {list(product.missing_codes)} and any other code that isn't snow, clear or ocean ({F.OCEAN})",
        "start_doy": str(start_doy),
        "days_used": f"{len(doys)} (DOY {doys[0]}-{doys[-1]})",
        "missing_doys": ",".join(map(str, gaps)) or "none",
        "codes": f"{F.NEVER_SNOW} = never snow or ocean, {F.NEVER_MELTED} = never melted, {F.NODATA} = no data",
        "processing": "api/jobs/precompute_fdl.py + api/snow/fdl.py; chunks v1",
        "processed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    tags["source_granules"] = [granules[d] for d in sorted(granules)]
    return tags


def find_granules(tile, year, last_doy, product=products.DEFAULT):
    """{doy: {name, url, size, checksum}} for one tile-year, newest production if a day is listed twice."""
    end = date(year, 1, 1) + timedelta(days=last_doy - 1)
    results = earthaccess.search_data(
        short_name=product.short_name,
        version=product.version,
        temporal=(f"{year}-01-01", end.isoformat()),
        granule_name=product.granule_pattern(year, tile),
    )
    by_doy = {}
    for g in results:
        url = next((u for u in g.data_links() if u.endswith(product.extension)), None)
        if url is None:
            continue
        name = url.rsplit("/", 1)[-1]
        if f".{tile}." not in name or not name.startswith(
            f"{product.short_name}.A{year}"
        ):
            continue
        doy = F.doy_of(Path(name))
        if doy > last_doy:
            continue
        info = [
            i
            for i in g["umm"]
            .get("DataGranule", {})
            .get("ArchiveAndDistributionInformation", [])
            if "Checksum" in i
        ]
        info = (
            info[0]
            if len(info) == 1
            else next((i for i in info if i.get("Name") == name), {})
        )
        entry = {
            "name": name,
            "url": url,
            "size": info.get("SizeInBytes"),
            "checksum": info.get("Checksum"),
        }
        # Names differ only in the production timestamp, so the larger name is the newer file.
        if doy not in by_doy or name > by_doy[doy]["name"]:
            by_doy[doy] = entry
    return by_doy


def fetch(g, dest, retries=5):
    """Download one granule, verifying size and checksum; retry with backoff."""
    algo = (
        g["checksum"]["Algorithm"].lower().replace("-", "") if g["checksum"] else None
    )
    for attempt in range(1, retries + 1):
        try:
            h = hashlib.new(algo) if algo else None
            with _session().get(g["url"], stream=True, timeout=(20, 120)) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                        if h:
                            h.update(chunk)
            if g["size"] and dest.stat().st_size != g["size"]:
                raise IOError(f"size {dest.stat().st_size} != catalog {g['size']}")
            if h and h.hexdigest().lower() != g["checksum"]["Value"].lower():
                raise IOError("checksum mismatch")
            return
        except Exception as e:
            dest.unlink(missing_ok=True)
            if attempt == retries:
                raise RuntimeError(
                    f"{g['name']}: failed after {retries} tries: {e}"
                ) from e
            time.sleep(2**attempt)


def _session():
    """One authenticated requests session per download thread."""
    if not hasattr(_local, "session"):
        _local.session = earthaccess.get_requests_https_session()
    return _local.session


def read_cgf(path, product=products.DEFAULT):
    """(tile transform, raw uint8 gap-filled NDSI) for one daily file of `product`."""
    with _hdf_lock:
        transform, data = granule_io.read_layer(path, product.layer)
    expected = (product.tile_pixels, product.tile_pixels)
    if data.shape != expected:
        raise ValueError(f"{path.name}: {product.layer} has shape {data.shape}, expected {expected}")
    if round(abs(transform.a), 3) != round(product.pixel_size, 3):
        raise ValueError(f"{path.name}: pixel size {transform.a} is not {product.key}'s {product.pixel_size}")
    return transform, data


if __name__ == "__main__":
    main()
