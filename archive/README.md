# archive

Everything that was in the repo before the 2026-10-06 restructure, moved here unchanged (`git mv`, so `git log --follow <file>` shows full history). Nothing here is maintained; the live code is in `api/`. The folders keep their relative paths to each other, so the demos still run from here.

| Path | Was | Committed by | Live version |
|---|---|---|---|
| `demo/` | Synthetic PCA prototype and watershed masking demo (`snowpca/`, `run_demo.py`, `watershed_demo.py`) | Joe Davitt, Tyler Osso | `api/snow/` (`dummy.py` → `synthetic.py`); boundary → `db/boundaries/` |
| `realdata/` | First real-data pipeline: `download.py`, `fdl.py`, `run_real.py`, `precompute_fdl.py`; its README has the first real results, timings and data-access findings | Joe Davitt (`precompute_fdl.py`: Christopher Bailey) | `api/snow/fdl.py`, `api/jobs/` |
| `MODIS-testing/` | earthaccess download and HDF reading scripts, plus 10 MOD10A1 h10v04 files | Christopher Bailey | Superseded by `api/jobs/` |
| `testing-demo/` | Matrix visualization demo (`pca_demo.py`) | cbalesohay | — |
| `repo-analysis/`, `repo-workflow.md` | GitHub URL-swap tooling notes (gitdiagram, gitingest, deepwiki, gitmcp) | Tyler Osso | — |
| `data/` | Sample MOD10A1, MYD10A1, VNP10A1, VJ110A1 granules for h09v04 (about 60 MB), `manifest.json`, preview PNGs | Tyler Osso | — |
| `requirements.txt` | Old root requirements (numpy, matplotlib, pyhdf, earthaccess) | Christopher Bailey, cbalesohay | `api/requirements.txt` |

To run an archived demo, e.g. `cd archive/demo` then `python run_demo.py` (needs numpy, matplotlib, rasterio).

**Open for the team:** `data/` and `MODIS-testing/downloads/` hold raw HDF/H5 files, which the repo rules say shouldn't be in version control. They're kept for now so nothing is lost. Untracking them stops new copies but doesn't shrink history; decide together.
