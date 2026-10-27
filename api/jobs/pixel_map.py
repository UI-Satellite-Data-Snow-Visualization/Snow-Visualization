"""Clickable native-grid watershed map for the terminal workbench."""
import json

import numpy as np


def create_pixel_map(result, recompute=None):
    """Transform cell corners for display; retain original raster values and click indices."""
    import matplotlib.pyplot as plt
    from matplotlib.widgets import RadioButtons, TextBox, Button
    from jobs.tui import describe
    from rasterio.warp import transform
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    grid, mask, annual, pc1, out = result
    metadata = json.loads((out / 'settings.json').read_text())
    years = list(annual)
    layers = {f'FDL {year}': np.where(mask & (fdl > 0) & (fdl < 365), fdl, np.nan)
              for year, (fdl, _) in annual.items()}
    layers['PC1'] = pc1
    fig = plt.figure(figsize=(13, 8))
    ax = fig.add_axes([.06, .18, .53, .65])
    panel = fig.add_axes([.69, .73, .29, .15])
    source = metadata.get('source', 'unknown source')
    fig.suptitle(f'Watershed pixel explorer | {source} | NDSI {metadata["threshold"]:g}')
    threshold_box = TextBox(fig.add_axes([.17, .915, .09, .035]), 'NDSI threshold ',
                            initial=f'{metadata["threshold"]:g}')
    apply_button = Button(fig.add_axes([.28, .915, .14, .035]), 'Apply + recalculate')
    status = fig.text(.44, .928, 'Snow = NDSI >= threshold. Apply saves a new run.', fontsize=9)
    current_result = [result]
    progress_ax = fig.add_axes([.06, .115, .53, .018])
    progress_ax.set(xlim=(0, 100), ylim=(0, 1), xticks=[], yticks=[])
    progress_ax.set_facecolor('#e5e7eb')
    progress_fill = progress_ax.barh(.5, 0, height=1, color='#2563eb')[0]
    progress_text = fig.text(.06, .087, '100% | Ready', fontsize=9)
    progress_fill.set_width(100)
    ax.set_facecolor('#e5e7eb')
    first = next(iter(layers))
    state = {'layer': first, 'projection': 'Pixel grid', 'selected': None, 'artists': [], 'busy': False}
    center_x, center_y = grid.transform * (mask.shape[1] / 2, mask.shape[0] / 2)
    lon, lat = transform(grid.crs, 'EPSG:4326', [center_x], [center_y])
    zone = min(60, max(1, int((lon[0] + 180) // 6) + 1))
    projections = {'Pixel grid': None, 'MODIS sinusoidal': grid.crs,
                   'Longitude / latitude': 'EPSG:4326', 'Web Mercator': 'EPSG:3857',
                   f'Local UTM zone {zone}': f'EPSG:{(32600 if lat[0] >= 0 else 32700) + zone}'}
    rr, cc = np.indices((mask.shape[0] + 1, mask.shape[1] + 1))
    native_x, native_y = grid.transform * (cc, rr)
    coordinates = {'Pixel grid': (cc - .5, rr - .5)}
    for label, crs in projections.items():
        if crs is not None:
            xx, yy = transform(grid.crs, crs, native_x.ravel().tolist(), native_y.ravel().tolist())
            coordinates[label] = (np.asarray(xx).reshape(cc.shape), np.asarray(yy).reshape(rr.shape))
    marker, = ax.plot([], [], marker='s', markersize=9, markerfacecolor='none',
                      markeredgecolor='#ef4444', markeredgewidth=1.5, linestyle='none')
    ax.set_xlabel('Pixel column'); ax.set_ylabel('Pixel row')
    ax.set_title(first)
    image = ScalarMappable(norm=Normalize(), cmap='Blues_r')
    colorbar = fig.colorbar(image, ax=ax, fraction=.04, pad=.03)
    colorbar.set_label('FDL day of year')
    radio = RadioButtons(panel, list(layers))
    panel.set_title('Display layer', loc='left')
    projection_panel = fig.add_axes([.69, .52, .29, .16])
    projection_radio = RadioButtons(projection_panel, list(projections))
    projection_panel.set_title('Map coordinates / projection', loc='left')
    details = fig.text(.69, .47, 'SELECTED PIXEL\nClick inside the watershed.',
                       fontsize=10, family='monospace', va='top',
                       bbox=dict(facecolor='#f0fdf4', edgecolor='#86a98c', pad=10))
    fig.text(.06, .04, 'Gray: outside watershed | Pale green: no valid melt date | Red square: selected cell\n'
             'Click to inspect. Turn toolbar zoom/pan off before selecting. Close window to return.',
             fontsize=10, va='bottom')

    def display_point(row, col):
        crs = projections[state['projection']]
        if crs is None:
            return col, row
        x, y = grid.transform * (col + .5, row + .5)
        xx, yy = transform(grid.crs, crs, [x], [y])
        return xx[0], yy[0]

    def redraw():
        label = state['layer']
        values = layers[label]
        for artist in state['artists']:
            artist.remove()
        xx, yy = coordinates[state['projection']]
        background = ax.pcolormesh(xx, yy, np.where(mask, 1., np.nan), cmap='Greens', vmin=0, vmax=3, shading='flat')
        valid = values[np.isfinite(values)]
        lo, hi = (float(valid.min()), float(valid.max())) if valid.size else (0., 1.)
        image.set_clim(lo, hi if hi > lo else lo + 1)
        cells = ax.pcolormesh(xx, yy, values, cmap=image.cmap, norm=image.norm, shading='flat')
        centers_x = (xx[:-1, :-1] + xx[1:, 1:]) / 2
        centers_y = (yy[:-1, :-1] + yy[1:, 1:]) / 2
        outline = ax.contour(centers_x, centers_y, mask.astype(float), levels=[.5], colors=['#14532d'], linewidths=.8)
        state['artists'] = [background, cells, outline]
        ax.set_xlim(float(xx.min()), float(xx.max()))
        if state['projection'] == 'Pixel grid':
            ax.set_ylim(float(yy.max()), float(yy.min()))
            ax.set_xlabel('Pixel column'); ax.set_ylabel('Pixel row')
            ax.set_aspect('equal')
        else:
            ax.set_ylim(float(yy.min()), float(yy.max()))
            geographic = state['projection'] == 'Longitude / latitude'
            ax.set_xlabel('Longitude (degrees)' if geographic else 'Easting / X (meters)')
            ax.set_ylabel('Latitude (degrees)' if geographic else 'Northing / Y (meters)')
            ax.set_aspect(1 / np.cos(np.deg2rad(lat[0])) if geographic else 'equal')
            ax.ticklabel_format(style='plain', useOffset=False)
        if state['selected'] is not None:
            x, y = display_point(*state['selected'])
            marker.set_data([x], [y])
        colorbar.set_label('Relative melt timing (higher = later)' if label == 'PC1' else 'FDL day of year')
        ax.set_title(f'{label} | {state["projection"]}')
        fig.canvas.draw_idle()

    def change_layer(label):
        if state['busy']:
            return
        state['layer'] = label
        redraw()

    def change_projection(label):
        if state['busy']:
            return
        state['projection'] = label
        redraw()
        toolbar = getattr(fig.canvas, 'toolbar', None)
        if toolbar is not None:
            toolbar.update()

    def click(event):
        if state['busy']:
            return
        if event.inaxes is not ax or event.xdata is None or event.ydata is None or event.button != 1:
            return
        toolbar = getattr(fig.canvas, 'toolbar', None)
        if toolbar is not None and toolbar.mode:
            details.set_text('SELECTION PAUSED\nTurn off Zoom or Pan in the\ntoolbar, then click a cell.')
            fig.canvas.draw_idle()
            return
        crs = projections[state['projection']]
        if crs is None:
            col, row = int(np.floor(event.xdata + .5)), int(np.floor(event.ydata + .5))
        else:
            xx, yy = transform(crs, grid.crs, [event.xdata], [event.ydata])
            col_f, row_f = ~grid.transform * (xx[0], yy[0])
            if not np.isfinite([col_f, row_f]).all():
                return
            col, row = int(np.floor(col_f)), int(np.floor(row_f))
        if not (0 <= row < mask.shape[0] and 0 <= col < mask.shape[1]) or not mask[row, col]:
            details.set_text('OUTSIDE WATERSHED\nClick a colored or pale-green\ncell inside the green outline.')
        else:
            state['selected'] = (row, col)
            px, py = display_point(row, col)
            marker.set_data([px], [py])
            x, y = grid.transform * (col + .5, row + .5)
            lines = [f'SELECTED PIXEL: {row}, {col}', f'Center: {x:.1f}, {y:.1f} m', 'MODIS sinusoidal coordinates', '']
            for year in years:
                fdl, lds = annual[year]
                lines.extend([f'{year}: FDL {describe(int(fdl[row, col]), year)}',
                              f'      LDS {describe(int(lds[row, col]), year)}'])
            lines.append(f'PC1: {pc1[row, col]:.4f}\nRelative timing (higher = later)' if np.isfinite(pc1[row, col])
                         else 'PC1: unavailable\nNeeds multiple valid years.')
            text = '\n'.join(lines)
            details.set_text('\n'.join(lines[:12]) + ('\nMore years printed in terminal.' if len(lines) > 12 else ''))
            print(text, flush=True)
        fig.canvas.draw_idle()

    def apply_threshold(_event):
        nonlocal annual, pc1, out, metadata
        if state['busy']:
            return
        def update_progress(percent, label):
            progress_fill.set_width(percent)
            progress_text.set_text(f'{percent}% | {label}')
            fig.canvas.draw_idle()
            fig.canvas.flush_events()
        try:
            threshold = float(threshold_box.text)
            if not np.isfinite(threshold) or not 0 < threshold <= 100:
                raise ValueError('Enter a threshold greater than 0 and at most 100.')
            if threshold == metadata['threshold']:
                status.set_text('This threshold is already displayed.')
                fig.canvas.draw_idle()
                return
            status.set_text('Recalculating from daily inputs; please wait...')
            state['busy'] = True
            apply_button.eventson = False
            fig.canvas.draw()
            fig.canvas.flush_events()
            from dataclasses import fields
            from jobs.tui import Settings, process
            values = {field.name: metadata[field.name] for field in fields(Settings)}
            values['years'] = tuple(values['years'])
            values['threshold'] = threshold
            updated = (recompute or process)(Settings(**values), progress=update_progress)
            new_grid, new_mask, new_annual, new_pc1, new_out = updated
            if new_grid != grid or not np.array_equal(new_mask, mask):
                raise ValueError('Recalculated grid differs from this map; reopen the explorer.')
            new_metadata = json.loads((new_out / 'settings.json').read_text())
            annual, pc1, out, metadata = new_annual, new_pc1, new_out, new_metadata
            current_result[0] = updated
            for year, (fdl, _) in annual.items():
                layers[f'FDL {year}'] = np.where(mask & (fdl > 0) & (fdl < 365), fdl, np.nan)
            layers['PC1'] = pc1
            redraw()
            fig.suptitle(f'Watershed pixel explorer | {source} | NDSI {threshold:g}')
            state['busy'] = False
            if state['selected'] is not None:
                px, py = display_point(*state['selected'])
                click(SimpleNamespace(inaxes=ax, xdata=px, ydata=py, button=1))
            status.set_text(f'Applied NDSI {threshold:g}. New outputs saved.' +
                            (' High thresholds may give sparse results.' if threshold > 50 else ''))
        except Exception as exc:
            progress_text.set_text('Failed: calculation stopped. Previous map retained; see terminal.')
            status.set_text('Could not apply threshold; previous results remain. See terminal.')
            print(f'NDSI update failed: {exc}', flush=True)
        finally:
            state['busy'] = False
            apply_button.eventson = True
            fig.canvas.draw_idle()

    change_layer(first)
    fig.canvas.mpl_connect('button_press_event', click)
    radio.on_clicked(change_layer)
    projection_radio.on_clicked(change_projection)
    apply_button.on_clicked(apply_threshold)
    # Keep widget callbacks alive for the lifetime of the figure.
    fig._snow_radio = radio
    fig._snow_click = click
    fig._snow_projection = projection_radio
    fig._snow_display_point = display_point
    fig._snow_threshold = threshold_box
    fig._snow_apply_threshold = apply_threshold
    fig._snow_apply_button = apply_button
    fig._snow_result = current_result
    fig._snow_status = status
    fig._snow_progress_text = progress_text
    # Populate the panel immediately so an empty panel cannot hide a click problem.
    from types import SimpleNamespace
    rows, cols = np.nonzero(mask)
    middle = len(rows) // 2
    click(SimpleNamespace(inaxes=ax, xdata=float(cols[middle]), ydata=float(rows[middle]), button=1))
    return fig, ax, click, details


def show_pixel_map(result):
    import matplotlib
    if str(matplotlib.get_backend()).lower() == 'agg':
        raise RuntimeError('Interactive maps need a desktop plotting backend (for example TkAgg).')
    import matplotlib.pyplot as plt
    fig, _, _, _ = create_pixel_map(result)
    print('Click inside the watershed in the map window. Close the map to return to the menu.')
    plt.show(block=True)
    plt.close(fig)
    return fig._snow_result[0]
