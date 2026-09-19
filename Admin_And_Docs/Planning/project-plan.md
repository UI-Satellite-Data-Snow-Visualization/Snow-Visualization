# Project plan

Draft planning aid, September 17, 2026. Milestones and acceptance criteria below are proposals, not an agreed schedule. No individual assignments or deadlines have been established.

## Sources and scope

The [project brief](../Project_Documents/51-UI%20CS-BE%20Qualls-Satellite%20Data%20Snow%20Visualization%20Web%20Tool.docx) defines requirements. The [September 15 meeting summary](../Meeting_Notes/1_Meeting_9_15_26.docx) records initial processing direction and the synthetic PCA task. See the [README](../../README.md) for research context and all four sources.

The minimum deliverable is a publicly accessible web tool that lets users select an Idaho watershed, MODIS or VIIRS, and a time period; obtains multiyear NSIDC snow-cover observations; generates and maps a recurring spatial snowmelt pattern; and exports a georeferenced raster. Include end-user feedback and an architecture that can expand beyond Idaho. The sponsor specifies the hosting platform.

Daily cloud-gap filling is a stretch goal. Pattern values express relative melt timing, not exact dates or snow-water volume.

## Proposed milestones

| Milestone | Work and dependencies | Proposed acceptance evidence |
| --- | --- | --- |
| 1. Scientific prototype | Start with synthetic data while awaiting sponsor samples; follow the [prototype plan](pca-prototype-plan.md). | Reproducible known-pattern recovery, explicit PCA conventions, and exact pixel-layout reconstruction. |
| 2. Data and algorithm agreement | Obtain sample data and existing first-land algorithm; resolve product versions, quality flags, threshold, annual melt window, and sensor strategy. | A documented configuration and a small sample with independently checked annual first-land outputs. |
| 3. Precomputation pilot | Following meeting direction, generate annual first-land layers before watershed clipping. Depends on storage and data access decisions. | A bounded pilot can resume and reuse outputs; layers record provenance and preserve alignment and missing-data masks. Measure runtime and storage before statewide expansion. |
| 4. Watershed processing | Obtain watershed boundaries; clip stored layers, construct PCA inputs, generate pattern and export. | For an agreed sample watershed, output location, dimensions, CRS, transform, mask, and relative timing convention are verified. |
| 5. Web workflow | Choose implementation stack and connect map selection, sensor, period, processing status, visualization, and download. | Demonstrate the full workflow for each supported sensor and clear responses to unavailable years or insufficient valid data. |
| 6. Public delivery | Establish sponsor hosting and storage; incorporate end-user feedback. | Public deployment is verified, exports open in a geospatial viewer, and setup, operating costs, data refresh, and known limitations are documented. |

An early MODIS pilot does not satisfy the final requirement for both sensor choices. Statewide coverage and supported periods must be explicitly agreed and demonstrated before claiming complete coverage.

## Dependencies and risks

- Sponsor inputs: sample data, existing first-land algorithm, map sources, hosting/storage arrangements, and scientific clarification.
- Persistent clouds and missing observations can bias annual timing; resolve quality and exclusion policies before interpreting results.
- Sensor grids and records differ; do not combine observations without an explicit harmonization decision.
- Statewide daily processing may exceed available resources; measure a pilot before selecting infrastructure or promising response times.
- PCA sign is arbitrary; apply and document a consistent display orientation.

Track answers in [decisions.md](decisions.md). Published study accuracy and explained variance are context, not application acceptance targets.

## Stretch goal

After the core workflow is validated, investigate fitting a pattern threshold to visible snow/land on a selected day and estimating cloud-obscured pixels. Define independent evaluation and failure behavior for poorly constrained images before claiming cloud-gap accuracy.
