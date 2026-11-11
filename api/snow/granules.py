"""Read one daily snow granule: MODIS HDF4 (.hdf) or VIIRS HDF-EOS5 (.h5).

Both formats carry an HDF-EOS StructMetadata.0 text block describing the grid,
and a uint8 NDSI layer with the same codes (0-100 NDSI, 237 inland water,
239 ocean, everything else unknown). The layer is returned as raw uint8 codes,
never converted, so flags stay flags. Needs pyhdf for .hdf and h5py for .h5.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from affine import Affine

from . import fdl as F

METADATA = "StructMetadata.0"


def read_layer(path: str | Path, layer: str,
               window: tuple[slice, slice] | None = None) -> tuple[Affine, np.ndarray]:
    """(tile transform, raw uint8 layer) for one daily file; window = (rows, cols) slices."""
    path = Path(path)
    if path.suffix.lower() == ".h5":
        return _read_hdf5(path, layer, window)
    if path.suffix.lower() == ".hdf":
        return _read_hdf4(path, layer, window)
    raise ValueError(f"{path.name}: unsupported file type (expected .hdf or .h5)")


def tile_transform(path: str | Path) -> Affine:
    """Tile transform from the grid metadata only, without reading the data layer."""
    path = Path(path)
    if path.suffix.lower() == ".h5":
        import h5py

        with h5py.File(path, "r") as f:
            return F.transform_from_struct_metadata(_metadata_text(f, path), path.name)
    return F.tile_transform(path)


def read_stack(files, window: tuple[slice, slice], layer: str) -> tuple[np.ndarray, np.ndarray]:
    """Daily layer for one window, as (doys, uint8 array of shape (T, H, W)), any product.

    Every file must share one tile transform; flags stay raw codes.
    """
    files = sorted(files, key=lambda p: F.doy_of(Path(p)))
    first, arrays = None, []
    for f in files:
        transform, data = read_layer(f, layer, window)
        if first is None:
            first = transform
        elif transform != first:
            raise ValueError(f"{Path(f).name}: grid differs from {Path(files[0]).name}")
        arrays.append(data)
    return np.array([F.doy_of(Path(f)) for f in files]), np.stack(arrays)


def _read_hdf4(path, layer, window):
    from pyhdf.SD import SD, SDC

    transform = F.tile_transform(path)
    sd = SD(str(path), SDC.READ)
    try:
        sds = sd.select(layer)
        F.require_uint8(sds, path)
        data = sds.get() if window is None else sds[window[0], window[1]]
        return transform, np.asarray(data, dtype=np.uint8)
    finally:
        sd.end()


def _read_hdf5(path, layer, window):
    import h5py

    with h5py.File(path, "r") as f:
        transform = F.transform_from_struct_metadata(_metadata_text(f, path), path.name)
        ds = find_dataset(f, layer, path)
        if ds.dtype != np.uint8:
            raise ValueError(f"{path.name}: layer {layer} is stored as {ds.dtype}, not uint8")
        data = ds[()] if window is None else ds[window[0], window[1]]
    return transform, np.asarray(data)


def find_dataset(f, layer: str, path: Path | str = "file"):
    """The one dataset named `layer`, wherever the HDF-EOS5 group tree puts it."""
    found = []
    f.visititems(lambda name, obj: found.append(name)
                 if name.rsplit("/", 1)[-1] == layer and hasattr(obj, "dtype") else None)
    if len(found) != 1:
        names = layer_names(f)
        problem = "not found" if not found else f"ambiguous ({found})"
        raise KeyError(f"{Path(path).name}: layer {layer} {problem}. Layers: {names}")
    return f[found[0]]


def layer_names(f) -> list[str]:
    """Names of all 2-D datasets in an HDF5 file (for error messages and inspection)."""
    names = []
    f.visititems(lambda name, obj: names.append(name)
                 if hasattr(obj, "shape") and len(obj.shape) == 2 else None)
    return names


def _metadata_text(f, path) -> str:
    found = []
    f.visititems(lambda name, obj: found.append(name)
                 if name.rsplit("/", 1)[-1] == METADATA else None)
    if not found:
        raise ValueError(f"{Path(path).name}: no {METADATA} grid metadata")
    value = f[found[0]][()]
    if isinstance(value, np.ndarray):
        value = value.item() if value.size == 1 else b"".join(value.ravel())
    if isinstance(value, bytes):
        value = value.decode("ascii", "replace")
    return str(value).rstrip("\x00")
