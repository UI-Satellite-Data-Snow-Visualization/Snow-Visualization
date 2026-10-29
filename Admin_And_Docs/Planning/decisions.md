# Decision register

Draft, September 17, 2026; reference-validation status updated October 13 and 20, 2026; sponsor direction relayed October 20, 2026; sponsor meeting October 29, 2026 (see Answers log). “Pending” means no answer has been established in the inspected project materials. Entries are questions to resolve, not instructions to contact anyone.

Evidence: [project brief](../Project_Documents/51-UI%20CS-BE%20Qualls-Satellite%20Data%20Snow%20Visualization%20Web%20Tool.docx), [meeting summary](../Meeting_Notes/1_Meeting_9_15_26.pdf), [team meeting](../Meeting_Notes/2_Meeting_9_22_26.pdf), [sponsor responses](../Project_Documents/Responses%20to%20Team%20Query-2026-09-29%20%281%29.docx), and research context in the [README](../../README.md).

| ID | Decision or question | Evidence and rationale | Status / answer |
| --- | --- | --- | --- |
| D01 | Which NDSI threshold(s), and may users select one? | Meeting explicitly leaves this open; 10 is an example. Threshold choice affects stored layers. | **Answered**: default 10 for FDL/PCA with an advanced option to change it; gap-fill threshold up to about 50–55 (see A1, A8) |
| D02 | Which MODIS/VIIRS products, collections, periods, and quality flags? | Brief requires both sensors and NSIDC; the paper's historical MODIS product is not a current product selection. | **Partly answered 2026-09-29**: MOD10A1F v61 for FDL, MOD10A1 v61 for cloud removal (see A2). **VIIRS direction 2026-10-29**: offer VIIRS (from 2012) alongside MODIS, pull VIIRS data early to test the code, and handle MODIS end of life with a clear message (A10). VIIRS product still open; gap-filled VNP10A1F and VJ110A1F v2 exist (team catalog check, 2026-10-28) |
| D03 | Keep sensor outputs separate or harmonize them? | Meeting asks how VIIRS fits the longer MODIS record. Resolution, alignment, and overlap need validation. | **Partly answered 2026-10-29**: keep them separate. The user toggles MODIS, VIIRS or both; with both, the maps are shown side by side for visual comparison, not pixel matching (A10). Whether records are ever combined in one PCA remains open |
| D04 | What defines first land, annual melt window, and returning snow behavior? | Meeting describes ignoring returning snow but also lists algorithm handling as unresolved. Inspect the existing algorithm and confirm with sponsor. | **Answered 2026-09-29** by the starter code: DOY 91 start, two-way search (see A3). **Start date under review 2026-10-29**: see D16 |
| D05 | How are clouds, missing days, never-snow and never-land pixels handled? | Annual timing requires an explicit valid-data policy; implementation proposal. | **Answered 2026-09-29**: flags are "unknown"; step a day at a time (see A3). Team fix needed for the 0/365 and NaN handling |
| D06 | What standardization, mask, and PC1 sign conventions should be used? | Meeting proposes column standardization. Missing-data behavior and numerical conventions need definition. | **Unresolved**: Woodruff's sklearn-on-raw-FDL = covariance PCA; Qualls expects years rescaled = correlation PCA (see A4, A8) |
| D07 | Where are statewide layers and the public application hosted? | Brief delegates platform selection to sponsor; meeting leaves storage open. | **Answered again 2026-10-29 (sponsor, in meeting)**: UI Research Computing and Data Services (RCDS) is likely to host. The sponsor will contact RCDS and arrange a meeting; RCDS may also work with the team. This restores A5 and supersedes the October 20 relay (A9). Resources and platform details pending (A10) |
| D08 | Which state/watershed boundaries, identifiers, and CRS? | Sponsor planned to coordinate map sources in meeting. | Pending. Constraint: PCA must use limited-size watersheds (A8). Sponsor accepts USGS WBD boundaries; HUC level open |
| D09 | Which language, libraries, frontend/backend, and job model? | Brief allows Python or another open-source language; no stack selected. | Pending. Sponsor allows Python or a faster compiled language if publicly deployable without licenses (A8) |
| D10 | What dataset size, response time, storage budget, and refresh cadence are acceptable? | Needed to size deployment; proposed engineering questions, not source requirements. | Pending |
| D11 | What sample outputs establish scientific acceptance? | Published study metrics do not establish application performance. | **Partly received / validation in progress, 2026-10-20**: 2000–2016 FDL/LDS mosaics and boundary supplied; no author PC1. PCA/SVD check completed (2026-10-13). Team FDL from daily MOD10A1F matches 97.9% of pixel-years exactly, and PC1 from team FDLs correlates 0.9998 with PC1 from Woodruff's (2026-10-20, [comparison report](woodruff-fdl-comparison-2026-10-20.md)). Agreed acceptance criteria remain outstanding (see A6). |
| D12 | What software license and confirmed contributor roster apply? | Source documents do not establish software licensing or full names/roles. | **Roster answered 2026-09-08** (see A7); license pending |
| D13 | Precompute annual first-land layers statewide per threshold, then clip by watershed. | Meeting design direction; evaluate feasibility with a bounded pilot. | **Confirmed and simplified 2026-09-29**: one threshold (10), large area, stored permanently (see A1) |
| D14 | Should SNOTEL stations appear on the output map, and with what information? | Sponsor request relayed 2026-10-20. NRCS AWDB API is public and returns Idaho stations with location, elevation and HUC12, plus daily SWE (team check, A9). | **Requested 2026-10-20** (secondhand, to confirm): small transparent markers that don't obscure data, showing station details on hover. Which values to show is open (the referenced iMap view shows SWE % of median). The markers weren't discussed on 2026-10-29, but SNOTEL came up for choosing the start date (D16) and for RCDS's related project (A10) |
| D15 | Should the tool warn when user settings may give unreliable results? | Sponsor request relayed 2026-10-20; users can change values such as the NDSI threshold. | **Requested 2026-10-20, to clarify with sponsor**: warnings that explain why a result may look strange or be inaccurate, e.g. a high threshold gives a spotty map. Which settings and limits trigger warnings is open (A9). Not revisited on 2026-10-29; the related request there is that unavailable sensor dates produce a clear message (A10) |
| D16 | How is the FDL start date chosen, per year and per watershed? | The fixed DOY 91 start gives odd results in some years (South Fork Boise 2022; Upper Snake 2013 mismatches). Sponsor goal since 2026-10-01. | **Exploration requested 2026-10-29**: near term, start about a week before SNOTEL peak snowpack at the basin's low-elevation stations; longer term, derive it from each pixel's longest continuous snow period, test whether elevation bands need separate dates, and measure compute cost (A10) |
| D17 | Which output graphics must the tool provide? | Sponsor listed them on 2026-10-29 while asking to avoid scope creep. | **Requested 2026-10-29, to confirm and scope**: per-year melt-date maps side by side, saved each year; PC1 map; an advanced page for custom year sets with GeoTIFF download; cloud-filled daily snow cover; a snow-line view with hard snow, hard land, an unknown band and the previous day's line; optionally a 3-D seasonal stack. Expo needs a live demo plus a backup video (A10) |

## Recording an answer

For each resolved item, record the answer, date, source or sponsor response, rationale, consequences, and affected artifacts. Preserve earlier answers when superseded. Assign owners and dates only when agreed.

## Answers log

- **A10 (D02, D03, D04, D07, D14, D16, D17), 2026-10-29, sponsor meeting** ([notes](../Meeting_Notes/6_Meeting_10_29_26.md), summarized from the recording's automatic transcript):
  - **Hosting (D07):** RCDS is likely to host. The sponsor will contact them and arrange a meeting, and will ask whether they want to work with the team directly. RCDS already supports a related project that uses this work to fill in snow information between SNOTEL stations.
  - **Start date (D16):** DOY 91 can miss early melt (2022 shown). Near term, start about a week before SNOTEL peak snowpack at low-elevation stations in the basin. Longer term, find each pixel's longest continuous snow period and derive a watershed start date (e.g. a median), testing whether elevation bands need separate dates and looking for a computationally efficient method.
  - **Graphics (D17):** see the D17 row. For the snow-line view, the tool must first decide whether a usable snow line is visible (e.g. a minimum length in pixels); if not, show the lowest contour where snow is seen, the highest where land is seen, the unknown band between, and the previous day's line if it was visible. Estimating the hidden line from nearby visible pixels was suggested as an alternative to compare. The sponsor suggested RCDS could help with the displays.
  - **Processing question:** whether to process daily images one at a time or as a stacked 3-D array (days x rows x columns). The current code already uses the stack.
  - **Gap-filled data:** using MOD10A1F for FDL/LDS is fine. `Cloud_Persistence` matters for displaying the snow line (observed or filled), not for FDL/LDS. He recalled the FDL/LDS PC1 correlation as about 99.999%; the 2019 paper reports 99.8%.
  - **VIIRS (D02, D03):** pull VIIRS data early to check whether one codebase can handle both sensors. Offer both, with a toggle and side-by-side display. Plan for MODIS end of life: a clear user message, an administrator switch for the end date, no automatic switch on short outages, and date pickers limited to each sensor's available range (team suggestion).
  - **Meetings:** as often as the team wants. He'll reach out after hearing from RCDS.
  - **Team discussion afterwards:** front-end and back-end in one repository or two, not decided (containers planned). Corrected in the notes: MOD10A1F has no elevation layer, so the snow-line contour view needs an external DEM.

- **A9 (D07, D14, D15), reported 2026-10-20: sponsor's comments to Matthew, relayed by Joe.** Secondhand: no notes or recording in the repo, and the meeting date isn't recorded. Treat as direction to confirm, not settled requirements.
  - **SNOTEL overlay (D14):** the sponsor wants SNOTEL stations on the outputs, as small transparent dots that don't obscure data, showing which station it is and relevant information on mouse hover. He pointed to NRCS's [iMap](https://nwcc-apps.sc.egov.usda.gov/imap/) (the shared view shows SNOTEL snow water equivalent as % of median, monthly).
    - Team check, 2026-10-20: the NRCS AWDB REST API (`https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/`) needs no login. `stations?stationTriplets=*:ID:SNTL&activeOnly=true` returned 87 active Idaho SNOTEL stations, each with name, latitude/longitude, elevation, HUC12 and begin date. `data?...&elements=WTEQ&duration=DAILY` returned daily SWE (inches).
    - The 2019 paper starts the FDL search at peak SWE at a SNOTEL station, so station data may also help automatic start-date detection.
  - **Hosting (D07):** it won't be hosted on school computers. He's talking with a few people about hosting; the two most likely weren't named in the relay. They will probably work on the code and ask the team questions, and are mostly interested in visualization. This conflicts with A5 (UI RCDS via IWRRI) until confirmed. *Superseded 2026-10-29 (A10): the sponsor said directly that RCDS is the likely host.*
  - **Warnings (D15):** because users can set values themselves, he wants messages explaining why a result may look strange or be inaccurate, e.g. a high threshold makes the map spotty. The team will re-clarify. Candidate triggers from existing evidence (team proposal, not sponsor-confirmed): threshold above about 50–55 (A1, A8), fewer than 3 years (Woodruff, Qualls & Clark 2026), a start date far from the default, an oversized watershed (A8), and many excluded pixels.

- **Reference data inspection, 2026-10-13 (D11; D06 remains unresolved):**
  The user supplied Woodruff's archive with 2000–2016 FDL/LDS mosaics and a
  watershed boundary. No reference PC1 is included. PCA on its 41,346 retained
  pixels explains 93.60% (covariance) / 93.68% (correlation); covariance agrees
  with independent SVD. This validates a numerical PCA check, not team FDL
  dates or agreement with author PC1. See
  [validation report](woodruff-validation-2026-10-13.md). Historical processing
  provenance and matching daily inputs are still needed.

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
