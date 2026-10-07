# Decision register

Draft, September 17, 2026; statuses updated October 1, 2026 (see Answers log). “Pending” means no answer has been established in the inspected project materials. Entries are questions to resolve, not instructions to contact anyone.

Evidence: [project brief](../Project_Documents/51-UI%20CS-BE%20Qualls-Satellite%20Data%20Snow%20Visualization%20Web%20Tool.docx), [meeting summary](../Meeting_Notes/1_Meeting_9_15_26.pdf), [team meeting](../Meeting_Notes/2_Meeting_9_22_26.pdf), [sponsor responses](../Project_Documents/Responses%20to%20Team%20Query-2026-09-29%20%281%29.docx), and research context in the [README](../../README.md).

| ID | Decision or question | Evidence and rationale | Status / answer |
| --- | --- | --- | --- |
| D01 | Which NDSI threshold(s), and may users select one? | Meeting explicitly leaves this open; 10 is an example. Threshold choice affects stored layers. | **Answered**: default 10 for FDL/PCA with an advanced option to change it; gap-fill threshold up to about 50–55 (see A1, A8) |
| D02 | Which MODIS/VIIRS products, collections, periods, and quality flags? | Brief requires both sensors and NSIDC; the paper's historical MODIS product is not a current product selection. | **Partly answered 2026-09-29**: MOD10A1F v61 for FDL, MOD10A1 v61 for cloud removal; VIIRS pending (see A2) |
| D03 | Keep sensor outputs separate or harmonize them? | Meeting asks how VIIRS fits the longer MODIS record. Resolution, alignment, and overlap need validation. | Pending |
| D04 | What defines first land, annual melt window, and returning snow behavior? | Meeting describes ignoring returning snow but also lists algorithm handling as unresolved. Inspect the existing algorithm and confirm with sponsor. | **Answered 2026-09-29** by the starter code: DOY 91 start, two-way search (see A3) |
| D05 | How are clouds, missing days, never-snow and never-land pixels handled? | Annual timing requires an explicit valid-data policy; implementation proposal. | **Answered 2026-09-29**: flags are "unknown"; step a day at a time (see A3). Team fix needed for the 0/365 and NaN handling |
| D06 | What standardization, mask, and PC1 sign conventions should be used? | Meeting proposes column standardization. Missing-data behavior and numerical conventions need definition. | **Unresolved**: Woodruff's sklearn-on-raw-FDL = covariance PCA; Qualls expects years rescaled = correlation PCA (see A4, A8) |
| D07 | Where are statewide layers and the public application hosted? | Brief delegates platform selection to sponsor; meeting leaves storage open. | **Partly answered 2026-09-29**: UI RCDS via IWRRI; details pending (see A5) |
| D08 | Which state/watershed boundaries, identifiers, and CRS? | Sponsor planned to coordinate map sources in meeting. | Pending. Constraint: PCA must use limited-size watersheds (A8). Sponsor accepts USGS WBD boundaries; HUC level open |
| D09 | Which language, libraries, frontend/backend, and job model? | Brief allows Python or another open-source language; no stack selected. | Pending. Sponsor allows Python or a faster compiled language if publicly deployable without licenses (A8) |
| D10 | What dataset size, response time, storage budget, and refresh cadence are acceptable? | Needed to size deployment; proposed engineering questions, not source requirements. | Pending |
| D11 | What sample outputs establish scientific acceptance? | Sponsor samples and algorithm are expected. Published study metrics do not establish application performance. | **In progress**: Upper Snake shapefile and 2000–2016 FDL/PC1 rasters promised 2026-10-05 (see A6) |
| D12 | What software license and confirmed contributor roster apply? | Source documents do not establish software licensing or full names/roles. | **Roster answered 2026-09-08** (see A7); license pending |
| D13 | Precompute annual first-land layers statewide per threshold, then clip by watershed. | Meeting design direction; evaluate feasibility with a bounded pilot. | **Confirmed and simplified 2026-09-29**: one threshold (10), large area, stored permanently (see A1) |

## Recording an answer

For each resolved item, record the answer, date, source or sponsor response, rationale, consequences, and affected artifacts. Preserve earlier answers when superseded. Assign owners and dates only when agreed.

## Answers log

Sources:
- `Responses to Team Query-2026-09-29 (1).docx` (Dr. Qualls, with Dr. Woodruff's replies pasted in)
- `FDL Processing Script Information-2026-09-02 (1).docx` (Woodruff)
- The instructor's assignment email (`Re_ Capstone Project 51 ... .msg`)
- `Starter_Code_FDL_LDS_MOD10A1F.py` (now `reference/`)

All are in `Admin_And_Docs/Project_Documents/` except the script, which is at the repo root. Earlier statuses are preserved in git history.

- **A1 (D01, D13), 2026-09-29, sponsor:**
  - The 2019 paper used an NDSI threshold of about 40. Later research found 10 (snow > 10, no-snow < 10) gives clearer, more robust FDLs and PCA models. Woodruff gives the rule as ≥ 10 = snow.
  - A PCA built at threshold 10 cloud-gap fills as well or better for thresholds up to about 55. So FDLs need computing only once, whatever threshold the user wants for cloud-gap filling.
  - FDLs/LDSs can be produced for very large areas (e.g., the mountainous western US) and saved permanently, then used for watershed-scale PCA.
  - Consequence: the planned per-threshold precompute is unnecessary.
- **A2 (D02), 2026-09-29, Woodruff:**
  - The script computes FDL/LDS from MOD10A1F v61 (cloud-gap filled). Cloud removal will use cloud-containing MOD10A1 v61, which MOD10A1F also carries as a layer.
  - VIIRS was not addressed.
- **A3 (D04, D05), 2026-09-02 and 2026-09-29, Woodruff and the script:**
  - Start mid-melt on DOY 91 (April 1).
  - Pixels that are snow on that day are searched forward for FDL. Pixels that are snow-free are searched backward. Pixels missing on that day are searched forward first, then backward if the first observation is snow-free.
  - Cloud and other flags are "unknown": move one day at a time until a 0–100 value appears.
  - Never melted = 365 (366 for leap years planned). Never snow = 0.
  - Forward-only processing from DOY 1 on MOD10A1F gave false early FDLs.
  - Team-found issues are recorded in the repo `CLAUDE.md`.
- **A4 (D06), 2026-09-29, Woodruff:** "We implemented the scikit learn PCA algorithm - actually a single value decomposition. We input directly the FDL matrices."
  - scikit-learn `PCA` centers each column but does not rescale it, so this describes covariance PCA. The 2026 papers project the raw FDL matrix onto the first eigenvector.
  - *Revised 2026-10-01:* this does **not** settle standardization. See A8.
- **A5 (D07), 2026-09-29, sponsor:** Long-term hosting is planned through UI Research Computing and Data Services (RCDS), arranged by the Idaho Water Resources Research Institute (IWRRI). Details are pending.
- **A6 (D11), 2026-09-29, Woodruff:**
  - Will share the Upper Snake shapefile and the 2000–2016 FDL and PC1 rasters "Monday of next week" (2026-10-05).
  - Recommends moving to the newest scripts rather than reproducing the 2019 paper. Updated FDL → PCA → cloud-removal scripts will be shared by 2026-10-16.
- **A7 (D12), 2026-09-08, instructor email:**
  - Team: Christopher Bailey, Joe Davitt, Matthew G. Fry, Tyler C. Osso (CS).
  - Capstone instructor: Dr. Yong (Steve) Wang.
  - Software license still pending.
- **A8 (D01, D06, D08, D09, and others), 2026-10-01, sponsor meeting** ([notes](../Meeting_Notes/3_Meeting_10_1_26.pdf), checked against the recording; known errors in the notes are listed in the repo `CLAUDE.md`):
  - **Threshold:** default 10 for FDL/PCA, with an advanced-user option to vary it. Gap-fill thresholds work "up through like 50 or so".
  - **PCA scaling (D06):** Qualls says each year must be centered *and rescaled* to the same melt duration, and believed the library does this automatically. scikit-learn's `PCA` does not rescale (verified 2026-10-01). On synthetic data, covariance and correlation PC1 give nearly the same melt order (rank r = 0.9995) but very different year weights (0.14–0.35 vs. 0.23–0.25). Unresolved until Woodruff's PCA script or reference PC1 is checked.
  - **Watershed scale (D08):** run PCA per limited-size watershed only. Regional snowpack anomalies confound PCA over large areas. FDLs can be computed for any area.
  - **Years:** FDLs are stored per year and appended annually. Advanced users may choose which years go into the PCA.
  - **Language (D09):** Python or a faster compiled language (e.g., C) is acceptable if publicly deployable without licenses.
  - **MOD10A1F:** cloud-gap fill carries the last observed value forward, and a metadata layer counts the days since the pixel was actually seen. Qualls guessed the script uses it; it does not (team check of the script).
  - **Beyond scope, welcome:** automatic start-date detection that works in either hemisphere, AI-assisted approaches, and global expansion with NSIDC adoption as a long-term goal.
