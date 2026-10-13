"""Inspect Woodruff's ZIP and compare PCA conventions on its FDL inputs.

Run from api/: python -m jobs.validate_woodruff --archive PATH
Reference rasters remain in the archive; generated rasters are not committed.
"""
import argparse
import hashlib
import io
import json
import platform
from pathlib import Path
import zipfile

import numpy as np
import rasterio
from rasterio.features import geometry_mask, geometry_window
from rasterio.io import MemoryFile
from rasterio.warp import transform_geom
import shapefile
from scipy.stats import spearmanr

from snow.matrix import build_matrix, to_raster
from snow.pca import run_pca


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path('output/woodruff_validation'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with args.archive.open('rb') as stream:
        archive_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = {'archive_sha256': archive_hash,
              'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'rasterio': rasterio.__version__},
              'scope': 'PCA on author FDL inputs; no independent FDL or reference PC1 comparison',
              'years': list(range(2000, 2017)), 'rasters': []}
    with zipfile.ZipFile(args.archive) as z:
        reader = shapefile.Reader(shp=io.BytesIO(z.read('Watershed_boundary/Watershed.shp')),
                                  shx=io.BytesIO(z.read('Watershed_boundary/Watershed.shx')),
                                  dbf=io.BytesIO(z.read('Watershed_boundary/Watershed.dbf')))
        geometries = [s.__geo_interface__ for s in reader.shapes()]
        report['boundary_features'] = len(geometries)
        boundary_crs = z.read('Watershed_boundary/Watershed.prj').decode()
        rasters = []
        baseline = None
        for year in report['years']:
            name = f'FDL_NDSI10/MOSAIC/FDL{year}_m.tif'
            with MemoryFile(z.read(name)) as mem, mem.open() as src:
                grid = (src.shape, src.crs, src.transform)
                if baseline is None:
                    baseline = grid
                    projected = [transform_geom(boundary_crs, src.crs, g) for g in geometries]
                    window = geometry_window(src, projected)
                    transform = src.window_transform(window)
                    shape = (int(window.height), int(window.width))
                    inside = geometry_mask(projected, shape, transform, invert=True, all_touched=False)
                    profile = src.profile.copy()
                    profile.update(height=shape[0], width=shape[1], transform=transform,
                                   dtype='float32', nodata=float('nan'), count=1)
                    report['grid'] = {'shape': src.shape, 'crs': str(src.crs),
                                      'transform': list(src.transform), 'crop_shape': shape}
                    report['boundary_pixels'] = int(inside.sum())
                elif grid != baseline:
                    raise ValueError(f'Grid mismatch: {name}')
                a = src.read(1, window=window).astype(float)
                values = a[inside]
                report['rasters'].append({'year': year, 'nodata': src.nodata,
                    'min': float(values.min()), 'max': float(values.max()),
                    'zero': int(np.sum(values == 0)), '365': int(np.sum(values == 365)),
                    '366': int(np.sum(values == 366))})
                # Conservative exclusion pending confirmation of historical codes.
                valid = inside & np.isfinite(a) & (a > 0) & (a < 365)
                if src.nodata is not None:
                    valid &= a != src.nodata
                a[~valid] = np.nan
                rasters.append(a)
        report['reference_pc1_present'] = any('pc1' in n.lower() for n in z.namelist())
    D, index = build_matrix(rasters)
    report['retained_pixels'] = len(D)
    report['retained_fraction'] = len(D) / report['boundary_pixels']
    report['mask'] = 'Pixel center inside supplied boundary; common finite record; exclude <=0 and >=365; no imputation'
    results = {}
    for label, correlation in [('covariance', False), ('correlation', True)]:
        result = run_pca(D, use_correlation=correlation, n_components=1)
        results[label] = result
        report[label] = {'explained_variance': result.explained_variance_ratio.tolist(),
                         'weights': result.weights().tolist(),
                         'year_correlations': result.year_correlations[:, 0].tolist()}
        with rasterio.open(args.out / f'pc1_{label}.tif', 'w', **profile) as dst:
            dst.write(to_raster(result.pc(), index).astype('float32'), 1)
        expected = to_raster(result.pc(), index).astype('float32')
        with rasterio.open(args.out / f'pc1_{label}.tif') as saved:
            assert saved.crs == baseline[1] and saved.transform == transform
            assert np.array_equal(saved.read(1), expected, equal_nan=True)
        report[label]['export_readback_verified'] = True
    # Independent SVD verification of covariance eigenvector and variance.
    centered = D - D.mean(0)
    _, singular, vt = np.linalg.svd(centered, full_matrices=False)
    w = vt[0]
    if w.sum() < 0:
        w = -w
    report['svd_check'] = {'max_weight_difference': float(np.max(np.abs(w - results['covariance'].weights()))),
        'max_variance_difference': float(np.max(np.abs(singular**2 / np.sum(singular**2) - results['covariance'].explained_variance_ratio)))}
    report['scaling_comparison'] = {
        'pearson': float(np.corrcoef(results['covariance'].pc(), results['correlation'].pc())[0, 1]),
        'spearman': float(spearmanr(results['covariance'].pc(), results['correlation'].pc()).statistic)}
    (args.out / 'results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
