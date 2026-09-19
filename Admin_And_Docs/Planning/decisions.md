# Decision register

Draft, September 17, 2026. “Pending” means no answer has been established in the inspected project materials. Entries are questions to resolve, not instructions to contact anyone.

Evidence: [project brief](../Project_Documents/51-UI%20CS-BE%20Qualls-Satellite%20Data%20Snow%20Visualization%20Web%20Tool.docx), [meeting summary](../Meeting_Notes/1_Meeting_9_15_26.docx), and research context in the [README](../../README.md).

| ID | Decision or question | Evidence and rationale | Status / answer |
| --- | --- | --- | --- |
| D01 | Which NDSI threshold(s), and may users select one? | Meeting explicitly leaves this open; 10 is an example. Threshold choice affects stored layers. | Pending |
| D02 | Which MODIS/VIIRS products, collections, periods, and quality flags? | Brief requires both sensors and NSIDC; the paper's historical MODIS product is not a current product selection. | Pending |
| D03 | Keep sensor outputs separate or harmonize them? | Meeting asks how VIIRS fits the longer MODIS record. Resolution, alignment, and overlap need validation. | Pending |
| D04 | What defines first land, annual melt window, and returning snow behavior? | Meeting describes ignoring returning snow but also lists algorithm handling as unresolved. Inspect the existing algorithm and confirm with sponsor. | Pending |
| D05 | How are clouds, missing days, never-snow and never-land pixels handled? | Annual timing requires an explicit valid-data policy; implementation proposal. | Pending |
| D06 | What standardization, mask, and PC1 sign conventions should be used? | Meeting proposes column standardization. Missing-data behavior and numerical conventions need definition. | Pending; experiment in prototype |
| D07 | Where are statewide layers and the public application hosted? | Brief delegates platform selection to sponsor; meeting leaves storage open. | Pending |
| D08 | Which state/watershed boundaries, identifiers, and CRS? | Sponsor planned to coordinate map sources in meeting. | Pending |
| D09 | Which language, libraries, frontend/backend, and job model? | Brief allows Python or another open-source language; no stack selected. | Pending |
| D10 | What dataset size, response time, storage budget, and refresh cadence are acceptable? | Needed to size deployment; proposed engineering questions, not source requirements. | Pending |
| D11 | What sample outputs establish scientific acceptance? | Sponsor samples and algorithm are expected. Published study metrics do not establish application performance. | Pending |
| D12 | What software license and confirmed contributor roster apply? | Source documents do not establish software licensing or full names/roles. | Pending |
| D13 | Precompute annual first-land layers statewide per threshold, then clip by watershed. | Meeting design direction; evaluate feasibility with a bounded pilot. | Documented direction; implementation unverified |

## Recording an answer

For each resolved item, record the answer, date, source or sponsor response, rationale, consequences, and affected artifacts. Preserve earlier answers when superseded. Assign owners and dates only when agreed.
