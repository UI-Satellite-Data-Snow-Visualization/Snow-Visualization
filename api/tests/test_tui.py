"""Workbench integration tests; all observations are synthetic."""
import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio

from jobs.tui import Settings, parse_years, process


class WorkbenchTests(unittest.TestCase):
    def test_threshold_changes_dates_and_exports_preserve_mask(self):
        with tempfile.TemporaryDirectory() as folder:
            updates = []
            low = process(Settings(years=(2020,), threshold=10), Path(folder),
                          progress=lambda percent, label: updates.append((percent, label)))
            self.assertEqual(updates[0][0], 0)
            self.assertEqual(updates[-1][0], 100)
            self.assertEqual([p for p, _ in updates], sorted(p for p, _ in updates))
            self.assertTrue(any('rows' in label for _, label in updates))
            self.assertTrue(any('Exported' in label for _, label in updates))
            high = process(Settings(years=(2020,), threshold=40), Path(folder))
            _, mask, annual, pc1, out = low
            self.assertTrue(np.all(high[2][2020][0][mask] < annual[2020][0][mask]))
            self.assertTrue(np.isnan(pc1).all())
            self.assertFalse((out / 'pc1.tif').exists())
            for kind, expected in zip(('fdl', 'lds'), annual[2020]):
                with rasterio.open(out / f'{kind}_2020.tif') as src:
                    np.testing.assert_array_equal(src.read(1), expected)
                    np.testing.assert_array_equal(src.dataset_mask() > 0, mask)
            with (out / 'pixels.csv').open() as stream:
                self.assertEqual(sum(1 for _ in csv.DictReader(stream)), int(mask.sum()))

    def test_multi_year_pca(self):
        with tempfile.TemporaryDirectory() as folder:
            result = process(Settings(), Path(folder))
            self.assertTrue(np.isfinite(result[3][result[1]]).all())
            self.assertTrue((result[-1] / 'settings.json').exists())
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from types import SimpleNamespace
            from jobs.pixel_map import create_pixel_map
            fig, ax, click, details = create_pixel_map(result, recompute=lambda settings, **kw: process(settings, Path(folder), **kw))
            row, col = np.argwhere(result[1])[0]
            from matplotlib.backend_bases import MouseEvent
            fig.canvas.draw()
            x, y = ax.transData.transform((col, row))
            event = MouseEvent('button_press_event', fig.canvas, x, y, button=1)
            fig.canvas.callbacks.process('button_press_event', event)
            self.assertIn(f'SELECTED PIXEL: {row}, {col}', details.get_text())
            self.assertIn('2020: FDL', details.get_text())
            for projection_index in range(1, 5):
                fig._snow_projection.set_active(projection_index)
                fig.canvas.draw()
                px, py = fig._snow_display_point(int(row), int(col))
                x, y = ax.transData.transform((px, py))
                event = MouseEvent('button_press_event', fig.canvas, x, y, button=1)
                fig.canvas.callbacks.process('button_press_event', event)
                self.assertIn(f'SELECTED PIXEL: {row}, {col}', details.get_text())
                self.assertIn('2020: FDL', details.get_text())
            fig._snow_projection.set_active(0)
            fig._snow_threshold.set_val('40')
            fig._snow_apply_threshold(None)
            updated = fig._snow_result[0]
            self.assertNotEqual(updated[-1], result[-1])
            self.assertTrue(np.all(updated[2][2020][0][result[1]] < result[2][2020][0][result[1]]))
            self.assertIn('Applied NDSI 40', fig._snow_status.get_text())
            self.assertIn('100%', fig._snow_progress_text.get_text())
            self.assertIn('NDSI 40', fig._suptitle.get_text())
            fig._snow_threshold.set_val('nan')
            fig._snow_apply_threshold(None)
            self.assertIs(fig._snow_result[0], updated)
            self.assertIn('Could not apply', fig._snow_status.get_text())
            row, col = np.argwhere(~result[1])[0]
            click(SimpleNamespace(inaxes=ax, xdata=float(col), ydata=float(row), button=1))
            self.assertIn('OUTSIDE WATERSHED', details.get_text())
            fig.savefig(result[-1] / 'map_test.png')
            plt.close(fig)

    def test_years_and_invalid_settings(self):
        self.assertEqual(parse_years('2020-2022,2021,2024'), (2020, 2021, 2022, 2024))
        for text in ('2022-2020', '', '1999', '2020-2021-2022'):
            with self.assertRaises(ValueError):
                parse_years(text)
        for settings in (Settings(threshold=0), Settings(threshold=101), Settings(start_doy=250)):
            with self.assertRaises(ValueError):
                process(settings)
