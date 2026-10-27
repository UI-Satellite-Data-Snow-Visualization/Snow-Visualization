"""Interactive snow-processing workbench. Run from api: python -m jobs.tui."""
from __future__ import annotations

import calendar
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from config import BOUNDARIES_DIR, RAW_DIR
from snow import build_matrix, run_pca, to_raster
from snow import fdl as F
from snow import watershed as ws
from jobs.run_real import tile_window, write_int16


@dataclass
class Settings:
    boundary: str = str(BOUNDARIES_DIR / 'wbd_huc8_17050113.geojson')
    years: tuple[int, ...] = (2020, 2021, 2022)
    threshold: float = 10
    start_doy: int = 91
    last_doy: int = 243
    correlation: bool = False
    demo: bool = True


def parse_years(text):
    years = set()
    for part in text.replace(',', ' ').split():
        ends = part.split('-')
        if len(ends) == 1:
            years.add(int(part))
        elif len(ends) == 2:
            first, last = map(int, ends)
            if last < first or last - first > 100:
                raise ValueError('Use ascending ranges of at most 101 years.')
            years.update(range(first, last + 1))
        else:
            raise ValueError('Use years like 2020-2022,2024.')
    if not years or min(years) < 2000 or max(years) > datetime.now(timezone.utc).year:
        raise ValueError('Choose years from 2000 through the current year.')
    return tuple(sorted(years))


def geometry(settings):
    boundary = ws.load_boundary(settings.boundary)
    shapes = ws.to_sinusoidal(boundary.geometries)
    grid = ws.grid_for(shapes)
    mask = ws.rasterize_mask(shapes, grid)
    if not mask.any():
        raise ValueError('Boundary contains no MODIS pixel centers.')
    tiles = ws.modis_tiles(mask, grid)
    if len(tiles) != 1:
        raise ValueError(f'This first TUI supports single-tile watersheds; found {tiles}.')
    return grid, mask, tiles[0]


def inventory(settings, tile):
    result = {}
    for year in settings.years:
        files = sorted(RAW_DIR.glob(f'MOD10A1F.A{year}*.{tile}.*.hdf'))
        files = [p for p in files if 1 <= F.doy_of(p) <= settings.last_doy]
        days = [F.doy_of(p) for p in files]
        expected = set(range(1, settings.last_doy + 1))
        if len(days) != len(set(days)):
            raise ValueError(f'{year}: duplicate daily files; keep one product version per day.')
        missing = sorted(expected - set(days))
        print(f'{year}: {len(files)}/{settings.last_doy} daily files; {len(missing)} missing')
        if missing:
            raise ValueError(f'{year}: download the complete requested season before processing.')
        result[year] = files
    return result


def synthetic_daily(grid, year, last_doy):
    """Artificial daily NDSI, never observational evidence; threshold changes melt dates."""
    row, col = np.indices(grid.shape)
    melt = 105 + 45 * row / max(1, grid.shape[0] - 1) + 25 * col / max(1, grid.shape[1] - 1)
    melt += 8 * np.sin(year) + 3 * np.cos(col / 12 + year)
    days = np.arange(1, last_doy + 1)
    stack = np.clip(50 + (melt[None] - days[:, None, None]) * 4, 0, 100).astype('uint8')
    stack[:, 0, 0] = 255
    return days, stack


def process(settings, output_root=None, progress=None):
    """Report completed work by phase, not an estimated percentage of elapsed time."""
    previous_percent = -1

    def report(percent, label):
        nonlocal previous_percent
        percent = int(percent)
        if percent != previous_percent:
            print(f'[{"#" * (percent // 5):20s}] {percent:3d}%  {label}', flush=True)
            previous_percent = percent
            if progress is not None:
                progress(percent, label)

    report(0, 'Preparing watershed and checking inputs')
    if not 0 < settings.threshold <= 100:
        raise ValueError('Threshold must be greater than 0 and at most 100.')
    if not 1 <= settings.start_doy <= settings.last_doy <= 365:
        raise ValueError('Require 1 <= start DOY <= last DOY <= 365.')
    grid, mask, tile = geometry(settings)
    files = {} if settings.demo else inventory(settings, tile)
    root = output_root or Path(__file__).resolve().parents[1] / 'output' / 'tui'
    out = root / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True, exist_ok=False)
    metadata = {**asdict(settings), 'source': 'SYNTHETIC' if settings.demo else 'MOD10A1F v61',
                'layer': 'CGF_NDSI_Snow_Cover', 'tile': tile, 'crs': grid.crs.to_wkt(),
                'transform': list(grid.transform), 'shape': grid.shape,
                'boundary_sha256': hashlib.sha256(Path(settings.boundary).read_bytes()).hexdigest(),
                'processing': 'jobs.tui.v1 / snow.fdl.fdl_lds',
                'mask': 'pixel centers inside watershed; PCA requires valid FDL in every year',
                'pc1': 'uncentered projection; weights sum positive; higher means later melt',
                'quality': 'cloud/night/fill unknown; no additional QA or Cloud_Persistence filtering',
                'inputs': {str(y): [p.name for p in paths] for y, paths in files.items()}}
    (out / 'settings.json').write_text(json.dumps(metadata, indent=2))
    annual, rasters = {}, []
    for year_number, year in enumerate(settings.years):
        base = 5 + 75 * year_number / len(settings.years)
        span = 75 / len(settings.years)
        report(base, f'{year}: reading daily observations')
        print(f'Processing {year} at NDSI {settings.threshold:g} ...', flush=True)
        if settings.demo:
            days, stack = synthetic_daily(grid, year, settings.last_doy)
        else:
            paths = files[year]
            first_transform = F.tile_transform(paths[0])
            window = tile_window(first_transform, grid)
            stack = np.empty((len(paths), *grid.shape), dtype=np.uint8)
            days = np.array([F.doy_of(p) for p in paths])
            for day_index, path in enumerate(paths):
                if F.tile_transform(path) != first_transform:
                    raise ValueError(f'{year}: input grid transforms differ.')
                _, daily = F.read_stack([path], window)
                stack[day_index] = daily[0]
                report(base + span * .6 * (day_index + 1) / len(paths),
                       f'{year}: read day {day_index + 1}/{len(paths)}')
        report(base + span * .6, f'{year}: calculating FDL/LDS')
        fdl = np.empty(grid.shape, dtype=np.int16)
        lds = np.empty_like(fdl)
        for start in range(0, grid.shape[0], 24):
            stop = min(start + 24, grid.shape[0])
            fdl[start:stop], lds[start:stop] = F.fdl_lds(stack[:, start:stop], days, settings.threshold, settings.start_doy)
            report(base + span * (.6 + .3 * stop / grid.shape[0]),
                   f'{year}: calculated rows {stop}/{grid.shape[0]}')
        del stack
        fdl[~mask] = lds[~mask] = F.NODATA
        for name, values in [('fdl', fdl), ('lds', lds)]:
            write_int16(out / f'{name}_{year}.tif', values, grid)
        annual[year] = (fdl, lds)
        valid = mask & ~np.isin(fdl, [F.NODATA, F.NEVER_SNOW, F.NEVER_MELTED])
        rasters.append(np.where(valid, fdl, np.nan))
        print(f'  {valid.sum():,} valid melt dates / {mask.sum():,} watershed pixels')
        report(base + span, f'{year}: annual rasters saved')
    pc1 = np.full(grid.shape, np.nan)
    report(80, 'Building multiyear pixel matrix')
    if len(settings.years) >= 2:
        try:
            matrix, index = build_matrix(rasters)
            if np.any(matrix.std(axis=0) == 0):
                raise ValueError('A year has no spatial variation.')
            report(84, 'Calculating PCA')
            result = run_pca(matrix, use_correlation=settings.correlation)
            report(88, 'Saving PC1 raster')
            pc1 = to_raster(result.pc(1), index)
            ws.write_geotiff(out / 'pc1.tif', pc1, grid)
            print(f'PC1 variance: {result.explained_variance_ratio[0]:.2%}; {matrix.shape[0]:,} pixels')
        except (ValueError, FloatingPointError) as exc:
            print(f'FDL/LDS available; PCA unavailable: {exc}')
    else:
        print('One year selected: FDL/LDS only; PCA requires at least two years.')
    report(90, 'Exporting pixel table')
    pixel_count = int(mask.sum())
    with (out / 'pixels.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['row', 'col', 'x', 'y', 'pc1'] + [f'{kind}_{y}' for y in settings.years for kind in ('fdl', 'lds')])
        for pixel_number, (row, col) in enumerate(zip(*np.nonzero(mask)), 1):
            x, y = grid.transform * (int(col) + .5, int(row) + .5)
            writer.writerow([row, col, x, y, float(pc1[row, col]) if np.isfinite(pc1[row, col]) else ''] +
                            [int(a[row, col]) for year in settings.years for a in annual[year]])
            if pixel_number % 500 == 0:
                report(90 + 9 * pixel_number / pixel_count, f'Exported {pixel_number:,}/{pixel_count:,} pixels')
    print(f'Saved: {out}\nCodes: -1 unknown; 0 never snow; 365 never melted. Coordinates are MODIS sinusoidal meters.')
    report(100, 'Complete: all outputs saved')
    return grid, mask, annual, pc1, out


def describe(value, year):
    if value in (-1, 0, 365):
        return {-1: 'unknown', 0: 'never snow', 365: 'never melted'}[value]
    from datetime import date, timedelta
    return f'DOY {value} ({date(year, 1, 1) + timedelta(days=value - 1)})'


def inspect_pixel(result):
    grid, mask, annual, pc1, _ = result
    print(f'Grid: {grid.shape[0]} rows x {grid.shape[1]} columns (zero-based).')
    print('A pixel is one satellite grid cell. Only cells inside the watershed can be inspected.')
    print('Enter row,col (for example 75,106); blank selects an inside pixel; q returns to the menu.')
    print('FDL = first day land (snow-free); LDS = last day snow before melt-out.')
    while True:
        answer = input('Pixel > ').strip()
        if answer.lower() == 'q':
            return
        try:
            if answer:
                row, col = map(int, answer.split(','))
            else:
                rows, cols = np.nonzero(mask)
                row, col = int(rows[len(rows) // 2]), int(cols[len(cols) // 2])
            if not (0 <= row < grid.shape[0] and 0 <= col < grid.shape[1] and mask[row, col]):
                raise ValueError('Choose a pixel inside the watershed.')
            print(f'Pixel {row},{col}; center {grid.transform * (col + .5, row + .5)}')
            for year, (fdl, lds) in annual.items():
                print(f'  {year}: FDL {describe(int(fdl[row, col]), year)}; LDS {describe(int(lds[row, col]), year)}')
            if np.isfinite(pc1[row, col]):
                print(f'  PC1: {pc1[row, col]:.4f} (relative timing: higher = later melt, not a date or snow volume)')
            else:
                print('  PC1: unavailable (requires multiple years and valid melt dates across all selected years).')
        except ValueError as exc:
            print(exc)


def main():
    settings, result = Settings(), None
    print('SNOW WORKBENCH | MODIS | q to quit')
    while True:
        print(f'\nMode: {"SYNTHETIC DEMO" if settings.demo else "REAL MODIS"} | Years: {settings.years}')
        print(f'Snow threshold: NDSI >= {settings.threshold:g} | Search anchor: day {settings.start_doy} | Observations: days 1-{settings.last_doy}')
        print(f'PCA scaling: {"correlation" if settings.correlation else "covariance"} | DOY = day of year (January 1 = 1)')
        print(f'Boundary: {settings.boundary}')
        print('Synthetic mode uses artificial snow observations; real mode uses downloaded NASA observations.' if settings.demo
              else 'Real mode uses local NASA MODIS observations. Download missing inputs with option 4.')
        print('\n1  Settings             Change years, snow threshold, watershed, search days, and PCA scaling.')
        print('2  Switch demo/real     Toggle artificial practice data and real MODIS observations.')
        print('3  Check local data     Check downloaded daily files for the selected watershed and years.')
        print('4  Download real data   Fetch missing NASA daily files; requires Earthdata login and disk space.')
        print('5  Run + export         Calculate per-pixel FDL/LDS; save GeoTIFFs, pixel CSV, and multiyear PC1.')
        print('6  Pick pixel on map    Click the watershed map to see annual melt dates from the last run.')
        print('7  Inspect by row,col   Type a grid position to inspect a pixel without opening a map.')
        print('q  Quit                 Close the workbench. Exported files remain on disk.')
        try:
            choice = input('> ').strip().lower()
            if choice == 'q':
                return
            if choice == '1':
                candidate = Settings(**asdict(settings))
                print('\nSETTINGS | Press Enter at any prompt to keep its current value.')
                print('Years: one year returns annual FDL/LDS. Two or more also allow a recurring pattern (PC1).')
                text = input(f'Years [current: {settings.years}; e.g. 2020-2022,2024]: ').strip()
                if text:
                    candidate.years = parse_years(text)
                for field, label, convert, explanation in [
                    ('threshold', 'NDSI snow threshold', float,
                     'Snow means NDSI >= this value; lower readings are snow-free. Flags stay unknown.\nDefault 10; try 20 or 40 to compare. Valid range: greater than 0 through 100.'),
                    ('start_doy', 'Search anchor DOY', int,
                     'The day from which the algorithm searches forward or backward for melt-out.\nThis is NOT the first input day. Default 91 (April 1 in a non-leap year).'),
                    ('last_doy', 'Last observation DOY', int,
                     'Read observations from January 1 THROUGH this day. Default 243 (late August).\nAn early cutoff misses later melt: code 365 then means no melt found by the cutoff.\nUsually keep this later than the anchor; it is not a single day to inspect.')]:
                    print(f'\n{explanation}')
                    text = input(f'{label} [current: {getattr(candidate, field)}]: ').strip()
                    if text:
                        setattr(candidate, field, convert(text))
                print('\nWatershed: a WGS84 longitude/latitude GeoJSON boundary. Only inside pixel centers are included.')
                print(f'Current: {candidate.boundary}')
                text = input('Boundary file path [Enter keeps current]: ').strip().strip('"')
                if text:
                    candidate.boundary = str(Path(text).resolve())
                print('\nPCA scaling affects how selected years contribute to the recurring melt pattern.')
                print('covariance: center each year, retaining its spread (default).')
                print('correlation: also rescale each year to equal spread. Sponsor choice is unresolved (D06).')
                text = input(f'PCA covariance/correlation [current: {"correlation" if candidate.correlation else "covariance"}]: ').strip().lower()
                if text:
                    if text not in ('covariance', 'correlation'):
                        raise ValueError('Choose covariance or correlation (D06 remains unresolved).')
                    candidate.correlation = text == 'correlation'
                if not 0 < candidate.threshold <= 100 or not 1 <= candidate.start_doy <= candidate.last_doy <= 365:
                    raise ValueError('Invalid threshold or day range; settings unchanged.')
                if any(candidate.last_doy > 365 + calendar.isleap(y) for y in candidate.years):
                    raise ValueError('Invalid end day.')
                geometry(candidate)
                settings = candidate
                print('Settings saved. Choose 5 to calculate new results; option 6 still shows the previous run.')
            elif choice == '2':
                settings.demo = not settings.demo
            elif choice == '3':
                _, _, tile = geometry(settings)
                inventory(settings, tile)
            elif choice == '4':
                print('Downloads daily MOD10A1F files into db/raw; about 0.55 GB per tile-year. Earthdata login required.')
                if input('Type download to proceed: ').strip().lower() == 'download':
                    from jobs.download import fetch_year, login
                    _, _, tile = geometry(settings)
                    login()
                    print('[                    ]   0%  Starting downloads', flush=True)
                    for year_index, year in enumerate(settings.years):
                        def download_progress(percent, label):
                            overall = int((year_index + percent / 100) * 100 / len(settings.years))
                            print(f'[{"#" * (overall // 5):20s}] {overall:3d}%  {label}', flush=True)
                        fetch_year(year, tile, settings.last_doy, RAW_DIR, progress=download_progress)
            elif choice == '5':
                if settings.threshold > 50:
                    print('Notice: high thresholds may produce sparse results; acceptance limits are not established.')
                if len(settings.years) == 1:
                    print('One year selected: annual FDL/LDS only. No multiyear pattern (PC1) will be calculated.')
                elif len(settings.years) < 3:
                    print('Notice: short year selections may not represent the recurring pattern well.')
                if settings.last_doy <= settings.start_doy:
                    print('Notice: the observation cutoff is at the search anchor; later melt cannot be detected.')
                result = process(settings)
            elif choice in ('6', '7'):
                if result is None:
                    print('Run processing first.')
                elif choice == '6':
                    try:
                        from jobs.pixel_map import show_pixel_map
                        result = show_pixel_map(result)
                    except ImportError as exc:
                        print(f'Map dependency unavailable: {exc}. Use option 7 for text inspection.')
                else:
                    inspect_pixel(result)
            else:
                print('Choose 1-7 or q.')
        except (ValueError, OSError, RuntimeError) as exc:
            print(f'Unable to complete: {exc}')
        except KeyboardInterrupt:
            print('\nCancelled; returning to menu.')


if __name__ == '__main__':
    try:
        main()
    except EOFError:
        print('\nGoodbye.')
