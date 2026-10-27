"""Download MOD10A1F v61 daily files for one MODIS tile from NSIDC.

    python -m jobs.download --years 2020 2021 2022 2023 2024     (run from api/)
    python -m jobs.download --years 2024 --tile h09v04 --last-doy 243

Needs an Earthdata login: the EARTHDATA_TOKEN environment variable
(get_EarthData_Access.md) or ~/.netrc. Files go to db/raw/ (see config.py; gitignored);
about 0.55 GB per tile-year for Jan-Aug. Files already present are skipped.
"""
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import earthaccess

from config import RAW_DIR


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--years", type=int, nargs="+", required=True)
    ap.add_argument("--tile", default="h09v04")
    ap.add_argument("--last-doy", type=int, default=243, help="last day of year to fetch (243 = Aug 31)")
    ap.add_argument("--out", type=Path, default=RAW_DIR)
    args = ap.parse_args()

    login()
    for year in args.years:
        fetch_year(year, args.tile, args.last_doy, args.out)


def fetch_year(year, tile, last_doy=243, out=RAW_DIR, progress=None):
    """Download one tile-year (DOY 1 to last_doy) into out, skipping files already there.

    Returns the paths downloaded by this call. Call login() first.
    """
    out.mkdir(parents=True, exist_ok=True)
    end = date(year, 1, 1) + timedelta(days=last_doy - 1)
    # Search by file-name pattern, then double-check the tile ID in each link.
    results = earthaccess.search_data(
        short_name="MOD10A1F", version="61", temporal=(f"{year}-01-01", end.isoformat()),
        granule_name=f"MOD10A1F.A{year}*.{tile}.061.*",
    )
    results = [g for g in results if f".{tile}." in g.data_links()[0]]
    have = {p.name for p in out.glob(f"MOD10A1F.A{year}*.{tile}.*.hdf")}
    todo = [g for g in results if g.data_links()[0].rsplit("/", 1)[-1] not in have]
    print(f"{year} {tile}: {len(results)} granules, {len(todo)} to download")
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
