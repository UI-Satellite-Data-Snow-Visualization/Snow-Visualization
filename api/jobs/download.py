"""Download daily snow files (MOD10A1F v61 by default, or VIIRS) for one tile from NSIDC.

    python -m jobs.download --years 2020 2021 2022 2023 2024     (run from api/)
    python -m jobs.download --years 2024 --tile h09v04 --last-doy 243
    python -m jobs.download --product viirs --years 2024        (VNP10A1F v2 HDF5)

Needs an Earthdata login: the EARTHDATA_TOKEN environment variable
(get_EarthData_Access.md) or ~/.netrc. Files go to db/raw/ (see config.py; gitignored);
about 0.55 GB per tile-year for Jan-Aug (MODIS). Files already present are skipped.
Each run also saves NASA's list of available days (<SHORTNAME>_<tile>_<year>_catalog.json
in the same folder), so the workbench can tell a real archive gap from an
unfinished download. Rerunning on a complete folder only refreshes that list.
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import earthaccess

from config import RAW_DIR
from snow import fdl as F
from snow import products


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--years", type=int, nargs="+", required=True)
    ap.add_argument("--tile", default="h09v04")
    ap.add_argument("--product", default=products.DEFAULT.key,
                    help="MOD10A1F.061 (default, modis), VNP10A1F.002 (viirs) or VJ110A1F.002")
    ap.add_argument("--last-doy", type=int, default=243, help="last day of year to fetch (243 = Aug 31)")
    ap.add_argument("--out", type=Path, default=RAW_DIR)
    args = ap.parse_args()

    try:
        product = products.get(args.product)
    except ValueError as err:
        ap.error(str(err))
    early = [y for y in args.years if y < product.first_year]
    if early:
        ap.error(f"{product.key} starts in {product.first_year}; no data for {early}")

    login()
    for year in args.years:
        fetch_year(year, args.tile, args.last_doy, args.out, product=product)


def fetch_year(year, tile, last_doy=243, out=RAW_DIR, progress=None, product=products.DEFAULT):
    """Download one tile-year (DOY 1 to last_doy) into out, skipping files already there.

    Returns the paths downloaded by this call. Call login() first.
    """
    product = products.get(product)
    out.mkdir(parents=True, exist_ok=True)
    end = date(year, 1, 1) + timedelta(days=last_doy - 1)
    # Search by file-name pattern, then double-check the tile ID in each link.
    results = earthaccess.search_data(
        short_name=product.short_name, version=product.version,
        temporal=(f"{year}-01-01", end.isoformat()),
        granule_name=product.granule_pattern(year, tile),
    )
    results = [g for g in results if f".{tile}." in _data_link(g, product)]
    write_catalog(out, product, tile, year, last_doy,
                  [F.doy_of(Path(_data_link(g, product).rsplit("/", 1)[-1])) for g in results])
    have = {p.name for p in out.glob(f"{product.short_name}.A{year}*.{tile}.*{product.extension}")}
    todo = [g for g in results if _data_link(g, product).rsplit("/", 1)[-1] not in have]
    print(f"{year} {tile} {product.short_name}: {len(results)} granules, {len(todo)} to download")
    if not todo:
        if progress:
            progress(100, f'{year}: all files already downloaded')
        return []
    if progress:
        downloaded = []
        progress(0, f'{year}: downloading {len(todo)} files')
        for start in range(0, len(todo), 8):
            batch = todo[start:start + 8]
            paths = earthaccess.download(batch, str(out), show_progress=False)
            if len(paths) != len(batch) or any(not Path(p).is_file() for p in paths):
                raise RuntimeError(f'{year}: download incomplete; retry to fetch missing files.')
            downloaded.extend(Path(p) for p in paths)
            progress(int(100 * len(downloaded) / len(todo)),
                     f'{year}: downloaded {len(downloaded)}/{len(todo)} missing files')
        return downloaded
    return [Path(p) for p in earthaccess.download(todo, str(out), show_progress=False)]

def catalog_path(folder, product, tile, year):
    return Path(folder) / f"{product.short_name}_{tile}_{year}_catalog.json"


def write_catalog(folder, product, tile, year, last_doy, doys):
    """Record which days NASA's catalog has for one tile-year (DOY 1 to last_doy)."""
    available = sorted({d for d in doys if 1 <= d <= last_doy})
    record = {"product": product.key, "tile": tile, "year": year, "searched_doys": [1, last_doy],
              "available_doys": available,
              "archive_gaps": sorted(set(range(1, last_doy + 1)) - set(available)),
              "searched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    catalog_path(folder, product, tile, year).write_text(json.dumps(record, indent=1))
    if record["archive_gaps"]:
        print(f"  NASA has no {product.short_name} file for {year} DOY {record['archive_gaps']}")


def read_catalog(folder, product, tile, year):
    """The saved catalog record, or None if this tile-year was never searched."""
    path = catalog_path(folder, product, tile, year)
    if not path.exists():
        return None
    record = json.loads(path.read_text())
    return record if record.get("product") == product.key else None


def _data_link(granule, product):
    """The granule's data file link (.hdf or .h5), skipping browse images and metadata."""
    links = granule.data_links()
    return next((u for u in links if u.endswith(product.extension)), links[0] if links else "")


def login():
    """Token or username/password from the environment first, then ~/.netrc. Never prompts."""
    for strategy in ("environment", "netrc"):
        try:
            if earthaccess.login(strategy=strategy).authenticated:
                return
        except Exception:
            pass
    sys.exit("No Earthdata login found. Set EARTHDATA_TOKEN (see get_EarthData_Access.md) "
             "or create ~/.netrc with: python -c \"import earthaccess; earthaccess.login(persist=True)\"")


if __name__ == "__main__":
    main()
