# Snow Cover 

**Web-Based Satellite-Observed Mountain Snow-Cover Visualization Tool**  
University of Idaho · Capstone Project 51 · 2026–2027

[![CI](https://github.com/UI-Satellite-Data-Snow-Visualization/Snow-Visualization/actions/workflows/ci.yml/badge.svg)](https://github.com/UI-Satellite-Data-Snow-Visualization/Snow-Visualization/actions/workflows/ci.yml)

Snow Cover is a web application in development for exploring recurring patterns of mountain snowmelt in Idaho. Users will select a watershed, satellite sensor, and time period. The tool will retrieve satellite snow-cover observations, calculate the spatial sequence of snowmelt across years, display the result on a map, and provide a georeferenced image for download. [1, 2]

The project brings the research of Craig D. Woodruff and Russell J. Qualls into a tool that water managers and other users can operate without writing their own processing code. Mountain snowmelt supplies about 75% of Idaho's water, making snow-cover information valuable for water management and drought assessment. [1, 3]

## Status (November 10, 2026)

| Component | State |
|---|---|
| PCA pipeline | South Fork Boise prototype completed. October 13: PCA on author FDL inputs agrees with independent SVD. October 20: team FDL matches 97.9% of author pixel-years exactly; PCA on team/author FDLs correlates 0.9998. No author PC1 supplied; D06 remains unresolved. See [comparison report](Admin_And_Docs/Planning/woodruff-fdl-comparison-2026-10-20.md). |
| FDL extraction | [`api/snow/fdl.py`](api/README.md): Dr. Woodruff's algorithm ([`reference/`](reference/README.md)) with the known data-handling issues fixed; tests check it matches his script. [8, 9] |
| Data access | NASA Earthdata via `earthaccess` ([`get_EarthData_Access.md`](get_EarthData_Access.md)). `api/jobs/precompute_fdl.py` downloads each tile-year once, computes FDL/LDS at thresholds 10–50 and keeps only the results in `db/`. MODIS and VIIRS. |
| Storage | SQLite database `db/fdl_store/snow.sqlite3` (decision D18): FDL/LDS as compressed 200 × 200 chunks on each product's native grid, one key per product, tile, year and threshold. The database is gitignored, so each machine fills its own; so far only h09v04 2023–2024 (MODIS and VIIRS) has been precomputed on team machines. Other Idaho tiles (h10v04, h10v03) not yet. |
| API | FastAPI (`api/server/`): products, watersheds, stored years, PCA, PC1 GeoTIFF and preview PNG, for MODIS or VIIRS. Runs locally only. |
| Web application | Local React + FastAPI prototype: watershed and sensor selection (MODIS or VIIRS, or both side by side), stored years and thresholds, PC1 preview and GeoTIFF download. No map yet; not hosted. |
| VIIRS | November 10: VNP10A1F (from 2012) and VJ110A1F v2 can be downloaded, precomputed and served on their native 375 m grid, separate from MODIS. Real VNP10A1F 2023–2024 precomputed for h09v04 (South Fork Boise: 24,593 pixels, PC1 95.0% at NDSI 10). Workbench and `run_real.py` also take VIIRS. VIIRS product choice (D02) still open. See [api/README.md](api/README.md#viirs-support-november-10-2026). |
| Local workbench | Menu-based terminal interface and clickable desktop pixel explorer in `api/jobs/`. Adjustable years, threshold, watershed and search days; FDL/LDS/PC1 exports, map projections and percentage progress. MODIS or VIIRS (sensor chosen in Settings); single-tile watersheds only. |
| Reference data | Supplied archive inspected October 13: 2000–2016 FDL/LDS mosaics and watershed boundary, collected locally under `db/validation/woodruff/` (gitignored). No reference PC1 supplied. Updated scripts were promised by October 16; receipt is not confirmed. [8] |

## Try the local workbench

Set up Python dependencies using [api/README.md](api/README.md#setup), then on
Windows double-click [Snow-Workbench.cmd](Snow-Workbench.cmd) in the repository
folder. From a terminal with the project environment active, run from `api/`:

```
python -m jobs.tui
```

It starts with **synthetic observations** for practice, using the South Fork
Boise watershed. Choose **1** for settings, **5** to calculate/export, and **6**
for a clickable map. Switch to real satellite data with **2**; **4** downloads the chosen
years using your Earthdata login. The map lets you inspect annual pixel dates,
change projection, and apply a new NDSI threshold. Calculations show percentage
progress. This local tool does not require a web server.

See the [workbench guide](api/README.md#interactive-terminal-workbench) for all
controls, defaults, file outputs, real-data setup and troubleshooting. Synthetic
results are not validation evidence. The publicly hosted web application remains
future work. To use VIIRS in the workbench, choose it at the first prompt of
option **1** (`viirs` = VNP10A1F, 2012 onward).

## Project scope

The core deliverable is an accessible web tool that generates and visualizes the **interannually recurring snowmelt pattern**: the relative order in which locations tend to become snow-free during spring melt. [1–3]

### Requirements

- Display a map of Idaho for the user to select a watershed and a satellite platform. Watershed selection is a core requirement.
- Choose MODIS or VIIRS observations and a time period.
- Retrieve multiple years of daily snow-cover data from the National Snow and Ice Data Center (NSIDC).
- Process the observations into a recurring snowmelt pattern.
- Display the pattern on an Idaho map, and allow download of a georeferenced raster, such as a GeoTIFF.
- Host the application on a publicly accessible platform specified by the sponsor.
- Refine usability through end-user feedback.
- Use Python or another open-source language, and code it so others can expand the work beyond Idaho. [1, 2]

### Stretch goal

Allow a user to select a day and estimate snow cover beneath clouds, using the recurring pattern and the visible part of that day's image. The brief lists this "as time allows". [1]

### Intended users

The project materials name the Idaho Department of Water Resources, Idaho Office of Emergency Management, NRCS SNOTEL, U.S. Army Corps of Engineers, Idaho Power, National Weather Service, NASA, and the Pacific Northwest Drought Early Warning System committee. These are intended audiences, not project partners. [1, 2]

## Scientific approach

The method comes from Woodruff and Qualls (2019) and the authors' later work. It uses **principal component analysis (PCA)** to extract the snowmelt pattern shared across years. The later papers call it the "dynamic seasonally recurrent snow depletion pattern". [3, 6, 7]

1. **Classify daily observations.** A pixel is snow when NDSI snow cover is **≥ 10**, and snow-free below 10. Advanced users may change this. Cloud and other flag values count as unknown, not as snow or land. The 2019 paper used a threshold of about 40; the authors have since moved to 10. [8]
2. **Find each year's first day of land (FDL).** The current script starts mid-melt on April 1 (DOY 91):
   - It searches forward for pixels that are snow on that day.
   - It searches backward for pixels that are already snow-free.
   - It ignores snow that returns after melt-out.
   - Pixels that never melt get 365; pixels that never had snow get 0.

   The meeting summary calls FDL "FTL". The last day of snow (LDS) is recorded alongside FDL. [3, 8, 9]
3. **Build a pixels-by-years matrix.** Flatten each year's FDL raster into one column, keeping the same pixel order and geographic alignment. [3, 5]
4. **Extract the recurring pattern.** Run PCA on the FDL matrix and project it onto the first eigenvector, then reshape the PC1 scores into a georeferenced image. The authors use scikit-learn's PCA, which centers each year but does not rescale it; Dr. Qualls describes each year as centered *and rescaled* to the same melt duration. Which scaling the tool uses is still being confirmed (decision D06). PCA runs per limited-size watershed, because snowpack differences between regions would confound it. [3, 6, 8, 11]
5. **Visualize relative melt timing.** Darker values melt earlier and lighter values later. The pattern shows relative timing, not calendar dates or snow-water volume. [3]
6. **Fill cloud gaps (stretch).**
   - Fit a cut-off on PC1 to the visible pixels of a selected day by minimizing visible-pixel error.
   - A pattern built at threshold 10 fills well for user thresholds up to about 50–55, including fractional ones.
   - Combining results across several thresholds gives a semi-continuous NDSI image.
   - Images more than 75% cloud are skipped. [6, 8]

### Evidence and limitations

- **2019 paper (Upper Snake River Basin):** 17 years of MODIS (2000–2016), evaluated on 2017–2018. PC1 explained **85%** of the variance, and spatial agreement was **84.9–97.5%**. [3]
- **2026 cloud-gap-filling paper (Upper Snake, 2000–2020):** 96.23% accuracy for continuous NDSI across thresholds 10–50. Its estimates of snow coverage were up to 10.8% lower than NASA's MOD10A1F gap-filled product. [6]
- **2026 drought paper (Boise River Basin, 2000–2024):** the pattern holds up under drought, with 98.7% correlation and cloud-gap-filling similarity of 96.73%, or 94.76% in severe drought. A pattern built from **as few as 3 years** correlates 98.7% with the 17-year model. [7]

These are research results, not measured performance of this application. The "~97%" variance figure in the September 15 meeting summary conflicts with the paper's 85% and is not a benchmark. Cloud-gap estimates depend on how much of the snow line is visible. [3–5]

## Data and processing design

| Area | Direction |
| --- | --- |
| FDL input | MOD10A1F v61 (NASA's cloud-gap-filled MODIS), `CGF_NDSI_Snow_Cover` layer [8, 9] |
| Cloud-removal input | Cloud-containing MOD10A1 v61, which MOD10A1F also carries as a layer [8] |
| VIIRS | Required by the brief. The sponsor wants VIIRS (from 2012) offered alongside MODIS, kept separate: users pick MODIS, VIIRS or both side by side. Implemented for gap-filled VNP10A1F v2 (Suomi NPP, from 2012; the default VIIRS choice) and VJ110A1F v2 (NOAA-20, from 2018), `CGF_NDSI_Snow_Cover`, 3000 × 3000 pixels per tile (~371 m). Which VIIRS product to offer is still open (D02). [1, 13] |
| Precomputation | Compute FDLs **once** over a large area covering every offered watershed, and store them permanently. The sponsor's default is threshold 10 [8]; the team also stores 20–50 from the same download for the advanced threshold option (A12). The sponsor notes FDLs can cover areas as large as the mountainous western US. This is the expensive step: about 1–2 minutes per tile-year with Woodruff's script; the team's VIIRS precompute took about 2 minutes per tile-year for all five thresholds on a home connection (2026-11-10), mostly download. [8, 9] |
| User processing | Clip stored FDLs to a limited-size watershed, run PCA (about 5 seconds for the Upper Snake), display, export. Advanced users may choose which years to include. [4, 8, 11] |
| Watersheds | USGS Watershed Boundary Dataset, with HUC8 likely. 60 of the 92 HUC8s touching Idaho cross a state line, so precompute coverage must extend past the state outline. HUC level is still to be confirmed. [2] |
| Hosting | UI Research Computing and Data Services (RCDS) is the likely host; the sponsor is arranging a first meeting with them. Details pending. [8, 13] |

## Repository contents

| Path | Contents |
|---|---|
| [`api/`](api/README.md) | All Python: the science (`snow/`), offline jobs and the local workbench (`jobs/`), the FastAPI server ([`server/`](api/server/README.md)), tests |
| [`client/`](client/README.md) | React + TypeScript + Vite front end (local prototype; no map yet) |
| [`db/`](db/README.md) | Stored data only: watershed boundaries; SQLite FDL store, raw downloads and validation data (gitignored) |
| [`reference/`](reference/README.md) | Sponsor's original code, unchanged (Woodruff's FDL/LDS script) |
| [`archive/`](archive/README.md) | Everything from before the 2026-10-06 restructure (demos, first real-data scripts, sample granules), unchanged |
| `get_EarthData_Access.md` | Earthdata login setup guide |
| `Admin_And_Docs/` | Project documents, meeting notes, planning, and the [decision register](Admin_And_Docs/Planning/decisions.md) |
| `CLAUDE.md`, `AGENTS.md` | Detailed project context and guidance for AI coding assistants |

Set up and run the tests (Windows shown; on macOS/Linux use `.venv/bin/`; with a uv-made environment use `uv pip install -r requirements.txt`). After pulling the VIIRS changes, reinstall the requirements: `h5py` is new.

```
cd api
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest
```

Job commands (precompute, download, end-to-end check) are in [`api/README.md`](api/README.md); running the web page locally is in [`client/README.md`](client/README.md).

## Next steps and open decisions

1. Add the Idaho map for choosing a watershed (a core requirement), and draw the PC1 preview on it.
2. Precompute the other Idaho tiles (h10v04, h10v03), add more watershed boundaries, and stitch tiles for watersheds that span two.
3. Prepare the Concept Design Review (MODIS/VIIRS side by side is a working demo) and ask the sponsor which VIIRS product to offer (D02).
4. Follow up on remaining 2013/2015 differences from the October 20 FDL comparison; compare author PC1 if supplied. Keep D06 unresolved.
5. Start-date method (D16), requested graphics (D17), SNOTEL markers (D14) and warnings (D15), as scoped with the sponsor.
6. Hosting with RCDS; a production setup needs a reverse proxy for `/api` (see `client/README.md`).

Still open (see the [decision register](Admin_And_Docs/Planning/decisions.md)):
- HUC level, and coverage of watersheds that cross state lines
- VIIRS product and its relationship to the MODIS record
- Web stack: a local FastAPI + React prototype is built, but D09 is not formally recorded in the register
- PCA scaling: covariance vs. correlation [11]
- Performance targets
- Software license
- Hosting details

## Team and acknowledgments

### Student team

Christopher Bailey, Joe Davitt, Matthew G. Fry, and Tyler C. Osso, all Computer Science. Three of the four are on the Coeur d'Alene campus, so team meetings are virtual. [10]

### Instructor

**Dr. Yong (Steve) Wang**, Professor and Chair, Department of Computer Science, is the capstone lead instructor. [10]

### Project sponsor

**Dr. Russell J. Qualls**, Associate Professor of Chemical & Biological Engineering and Idaho State Climatologist, University of Idaho. Contact: [rqualls@uidaho.edu](mailto:rqualls@uidaho.edu). [2, 10]

### Research foundation

**Dr. Craig D. Woodruff** (Wilfrid Laurier University), Dr. Qualls's former graduate student, developed the method with Dr. Qualls and wrote the FDL processing script. His collaboration on the method and code is credited here; he is not a repository contributor. [3, 8, 9]

## Source documents

Project documents are in `Admin_And_Docs/Project_Documents/`; meeting notes are in `Admin_And_Docs/Meeting_Notes/`.

1. **Project brief:** `51-UI CS-BE Qualls-Satellite Data Snow Visualization Web Tool.docx`. Scope, design requirements, intended users, stretch goal.
2. **Project presentation:** `Snow Cover Project Presentation.pptx`. Sponsor, workflow, user options, and an Idaho HUC8 watershed map.
3. **Woodruff, C. D., & Qualls, R. J. (2019).** *Recurrent snowmelt pattern synthesis using principal component analysis of multiyear remotely sensed snow cover.* Water Resources Research, 55, 6869–6885. [doi:10.1029/2018WR024546](https://doi.org/10.1029/2018WR024546)
4. **Sponsor meeting, September 15, 2026:** `1_Meeting_9_15_26.pdf`. Processing direction and the synthetic-PCA task. Transcription quality was poor.
5. **Team meeting, September 22, 2026:** `2_Meeting_9_22_26.pdf`. earthaccess demo, MODIS flag values, and confirmation that matrix columns are years.
6. **Woodruff, C. D., Qualls, R. J., & Humes, K. S. (2026).** *Cloud gap filling for continuous normalized difference snow index snow cover using the dynamic seasonally recurrent snow depletion pattern over a mountainous watershed.* Remote Sensing Applications: Society and Environment, 42, 102062. [doi:10.1016/j.rsase.2026.102062](https://doi.org/10.1016/j.rsase.2026.102062)
7. **Woodruff, C. D., Qualls, R. J., & Clark (2026).** *Assessment of Drought Impacts on Remotely Sensed Seasonal Snow Depletion.* Hydrological Processes. [doi:10.1002/hyp.70392](https://doi.org/10.1002/hyp.70392)
8. **Responses to team query, September 29, 2026:** `Responses to Team Query-2026-09-29 (1).docx`. Answers from Dr. Qualls and Dr. Woodruff on threshold, PCA, hosting, and reference data.
9. **FDL script rationale, September 2, 2026:** `FDL Processing Script Information-2026-09-02 (1).docx`. Woodruff's notes on the FDL search design.
10. **Team assignment email thread:** `Re_ Capstone Project 51 ... Team Assignment (1).msg`. Roster, instructor, and meeting scheduling.
11. **Sponsor meeting, October 1, 2026:** `3_Meeting_10_1_26.pdf`. Walk-through of the team's questions: threshold, PCA scaling, watershed scale, hosting, language. A few known errors in it are listed in `CLAUDE.md`.
12. **Team discussion and capstone class, October 13, 2026:** [meeting notes](Admin_And_Docs/Meeting_Notes/5_Meeting_10_13_26.pdf). Portfolio submission guidance, Concept Design Review logistics, remote participation, sustainability and peer assessment; separately labeled reference-validation follow-up. Transcript has overlapping audio and unclear review dates.
13. **Sponsor meeting, October 29, 2026:** [meeting notes](Admin_And_Docs/Meeting_Notes/6_Meeting_10_29_26.md). Hosting with RCDS, choosing the FDL start date, requested graphics, VIIRS alongside MODIS. Decisions recorded in `Admin_And_Docs/Planning/decisions.md` (A10).
14. **Team meeting, October 6, 2026:** `4_Meeting_10_6_26.pdf`. Real-data demo, VIIRS, thresholds vs. storage, schedule, budget.
15. **Team meeting, November 10, 2026:** `7_Meeting_11_10_26.pdf`. Concept Design Review preparation, logbooks and one-on-ones, React/API and SQLite progress, VIIRS follow-up.

## License

No software license has been chosen yet. The research papers' publication rights do not define the software's license.
