"""Pull MOD10A1F tile-years from NSIDC and keep only the FDL/LDS rasters.

    python -m jobs.precompute_fdl --years 2020 2021 2022 2023 2024     (run from api/)
    python -m jobs.precompute_fdl --years 2001 --tiles h09v04 h10v04 --workers 16

For each tile-year: list the daily granules in NASA's catalog, download them in
parallel to a temporary folder, check each file against the catalog's size and
checksum (retrying on failure), read the CGF_NDSI_Snow_Cover layer into memory
and delete the file at once. Then compute FDL/LDS with fdl.py (same algorithm
as Woodruff's starter code) and write two int16 GeoTIFFs to db/fdl_store/ (see config.py).

Disk: only the files in flight (about 2.3 MB each) plus about 2-4 MB of output
per tile-year, instead of about 0.55 GB of raw HDF. RAM: about 2.5 GB for a
full 2400 x 2400 tile-year (1.4 GB daily stack + FDL in row strips).
Tile-years already in the store are skipped, so an interrupted run resumes.
Needs the same Earthdata login as download.py.
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
from snow import watershed as ws

PRODUCT, VERSION = "MOD10A1F", "61"
TILE_PIXELS = 2400
STRIP_ROWS = 400            # FDL runs in row strips; pixels are independent, so results are identical

_hdf_lock = threading.Lock()   # the HDF4 library isn't thread-safe; downloads run in parallel, reads don't
_local = threading.local()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--years", type=int, nargs="+", required=True)
    ap.add_argument("--tiles", nargs="+", default=["h09v04"])
    ap.add_argument("--threshold", type=float, default=10)
    ap.add_argument("--start-doy", type=int, default=91)
    ap.add_argument("--last-doy", type=int, default=243, help="last day of year to fetch (243 = Aug 31)")
    ap.add_argument("--workers", type=int, default=8, help="parallel downloads")
    ap.add_argument("--out", type=Path, default=FDL_STORE_DIR)
    ap.add_argument("--tmp", type=Path, default=None, help="folder for in-flight files (default: system temp)")
    ap.add_argument("--overwrite", action="store_true", help="recompute tile-years already in --out")
    args = ap.parse_args()

    login()
    args.out.mkdir(parents=True, exist_ok=True)
    for tile in args.tiles:
        for year in args.years:
            fdl_path = args.out / f"fdl_{tile}_{year}_t{args.threshold:g}.tif"
            if fdl_path.exists() and not args.overwrite:
                print(f"{tile} {year}: already in {args.out.name}/, skipped")
                continue
            process_tile_year(tile, year, args, fdl_path)


def process_tile_year(tile, year, args, fdl_path):
    t0 = time.perf_counter()
    granules = find_granules(tile, year, args.last_doy)
    if not granules:
        print(f"{tile} {year}: no granules in the catalog, skipped")
        return
    doys = np.array(sorted(granules))
    gaps = sorted(set(range(int(doys[0]), args.last_doy + 1)) - set(doys.tolist()))
    print(f"{tile} {year}: {len(doys)} granules (DOY {doys[0]}-{doys[-1]}, {len(gaps)} missing days)")

    stack = np.empty((len(doys), TILE_PIXELS, TILE_PIXELS), dtype=np.uint8)
    transforms = [None] * len(doys)

    with tempfile.TemporaryDirectory(dir=args.tmp, prefix=f"mod10a1f_{tile}_{year}_") as tmp:
        def work(i, doy):
            g = granules[doy]
            path = Path(tmp) / g["name"]
            fetch(g, path)
            try:
                transforms[i], stack[i] = read_cgf(path)
            finally:
                path.unlink(missing_ok=True)

        ex = ThreadPoolExecutor(args.workers)
        try:
            futures = [ex.submit(work, i, int(d)) for i, d in enumerate(doys)]
            for n, fut in enumerate(as_completed(futures), 1):
                fut.result()   # any failure (after retries) aborts this tile-year
                if n % 50 == 0 or n == len(futures):
                    print(f"  {n}/{len(futures)} files ({time.perf_counter() - t0:.0f} s)")
        except BaseException:
            ex.shutdown(wait=True, cancel_futures=True)
            raise
        ex.shutdown()
    t_pull = time.perf_counter() - t0

    # Every day must sit on the same grid before stacking.
    if len(set(transforms)) != 1:
        raise ValueError(f"{tile} {year}: daily files don't share one grid: {set(transforms)}")
    transform = transforms[0]

    fdl = np.empty((TILE_PIXELS, TILE_PIXELS), dtype=np.int16)
    lds = np.empty_like(fdl)
    for r in range(0, TILE_PIXELS, STRIP_ROWS):
        fdl[r:r + STRIP_ROWS], lds[r:r + STRIP_ROWS] = F.fdl_lds(
            stack[:, r:r + STRIP_ROWS], doys, args.threshold, args.start_doy)
    del stack

    tags = {
        "product": f"{PRODUCT} v{VERSION} (NSIDC), layer {F.LAYER}",
        "tile": tile, "year": str(year),
        "threshold": f"snow = NDSI {args.threshold:g}-100; clear = NDSI < {args.threshold:g} or {F.INLAND_WATER}; "
                     f"missing = {F.MISSING_CODES}",
        "start_doy": str(args.start_doy),
        "days_used": f"{len(doys)} (DOY {doys[0]}-{doys[-1]})",
        "missing_doys": ",".join(map(str, gaps)) or "none",
        "codes": f"{F.NEVER_SNOW} = never snow or ocean, {F.NEVER_MELTED} = never melted, {F.NODATA} = no data",
        "processing": "realdata/precompute_fdl.py + realdata/fdl.py",
        "processed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    write_int16(fdl_path, fdl, transform, {**tags, "layer": "FDL (first day land, DOY)"})
    write_int16(fdl_path.with_name(fdl_path.name.replace("fdl_", "lds_", 1)), lds, transform,
                {**tags, "layer": "LDS (last day snow, DOY)"})

    valid = fdl[(fdl != F.NEVER_SNOW) & (fdl != F.NEVER_MELTED) & (fdl != F.NODATA)]
    print(f"  pulled in {t_pull:.0f} s, total {time.perf_counter() - t0:.0f} s; "
          f"FDL median DOY {np.median(valid):.0f} over {valid.size:,} pixels -> {fdl_path.name}")


def find_granules(tile, year, last_doy):
    """{doy: {name, url, size, checksum}} for one tile-year, newest production if a day is listed twice."""
    end = date(year, 1, 1) + timedelta(days=last_doy - 1)
    results = earthaccess.search_data(
        short_name=PRODUCT, version=VERSION, temporal=(f"{year}-01-01", end.isoformat()),
        granule_name=f"{PRODUCT}.A{year}*.{tile}.061.*",
    )
    by_doy = {}
    for g in results:
        url = next((u for u in g.data_links() if u.endswith(".hdf")), None)
        if url is None:
            continue
        name = url.rsplit("/", 1)[-1]
        if f".{tile}." not in name or not name.startswith(f"{PRODUCT}.A{year}"):
            continue
        doy = F.doy_of(Path(name))
        if doy > last_doy:
            continue
        info = [i for i in g["umm"].get("DataGranule", {}).get("ArchiveAndDistributionInformation", [])
                if "Checksum" in i]
        info = info[0] if len(info) == 1 else next((i for i in info if i.get("Name") == name), {})
        entry = {"name": name, "url": url, "size": info.get("SizeInBytes"), "checksum": info.get("Checksum")}
        # Names differ only in the production timestamp, so the larger name is the newer file.
        if doy not in by_doy or name > by_doy[doy]["name"]:
            by_doy[doy] = entry
    return by_doy


def fetch(g, dest, retries=5):
    """Download one granule, verifying size and checksum; retry with backoff."""
    algo = g["checksum"]["Algorithm"].lower().replace("-", "") if g["checksum"] else None
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
                raise RuntimeError(f"{g['name']}: failed after {retries} tries: {e}") from e
            time.sleep(2 ** attempt)


def _session():
    """One authenticated requests session per download thread."""
    if not hasattr(_local, "session"):
        _local.session = earthaccess.get_requests_https_session()
    return _local.session


def read_cgf(path):
    """(tile transform, raw uint8 CGF NDSI) for one daily file."""
    from pyhdf.SD import SD, SDC

    with _hdf_lock:
        transform = F.tile_transform(path)
        sd = SD(str(path), SDC.READ)
        try:
            data = np.asarray(sd.select(F.LAYER).get(), dtype=np.uint8)
        finally:
            sd.end()
    if data.shape != (TILE_PIXELS, TILE_PIXELS):
        raise ValueError(f"{path.name}: {F.LAYER} has shape {data.shape}")
    return transform, data


def write_int16(path, array, transform, tags):
    """int16 GeoTIFF on the native MODIS grid; written to a temp name first so a crash leaves no partial file."""
    import rasterio

    part = path.with_suffix(".part.tif")
    with rasterio.open(part, "w", driver="GTiff", height=array.shape[0], width=array.shape[1], count=1,
                       dtype="int16", crs=ws.MODIS_CRS, transform=transform, nodata=F.NODATA,
                       compress="deflate", predictor=2, tiled=True) as dst:
        dst.write(array, 1)
        dst.update_tags(**tags)
    part.replace(path)


if __name__ == "__main__":
    main()
