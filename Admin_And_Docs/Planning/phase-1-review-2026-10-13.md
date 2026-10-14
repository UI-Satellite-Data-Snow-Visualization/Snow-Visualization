# Phase 1 Fall 2026 review

Reviewed October 13, 2026 against the live organization
[Project 1](https://github.com/orgs/UI-Satellite-Data-Snow-Visualization/projects/1),
all 37 issue descriptions and repository evidence. This is a proposed update
list; no GitHub statuses, dates, assignees or descriptions were changed.
The project title covers the entire Fall schedule, including phases 1–4.

## Live baseline

10 Done, 3 In Progress, 24 Todo. All 37 underlying issues are open, including
the Done items. Project Status and issue state are distinct; do not close issues
solely because the imported workbook labeled them Done. Team member and
Assignees agree on every displayed row. Target dates are blank; Start week and
Final week are chart anchors, not exact deadlines or actual completion dates.

Owners: Tyler (@tylero07) 12 tasks; Chris (@cbalesohay) 12; Matthew
(@blahblah-blah2305) 7; Joe (@j-davitt) 6. Counts do not measure effort.
No evidence establishes that another owner accepted any reassignment.

## Requirements tasks

| ID / issue | Live status / owner | Evidence and recommended update |
| --- | --- | --- |
| 1.1 / #1 | Done / Tyler | Roster documented; contract linked in document_list.md. Add actual contract evidence; retain recorded status pending verification. |
| 1.2 / #2 | Done / Tyler | September 15 sponsor meeting notes exist. Link them; retain week-of-September-14 anchor. |
| 1.3 / #3 | In Progress / Matthew | Papers and substantial synthesis exist in README/CLAUDE. Close initial review only after Matthew confirms its deliverable; track future learning separately. October 5 final-week anchor has passed; propose finishing or reviewing the synthesis during week of October 12 rather than an indefinite literature task. |
| 1.4 / #4 | Done / Matthew | Value proposition linked externally; attach/link submission evidence. Do not infer missing work from absence in repo. |
| 1.5 / #5 | Done / Chris | PRD linked externally; verify measurable requirements and link submission. Future revisions should be separate follow-up work. |
| 1.6 / #6 | Done / Chris | Decision register, sponsor answers and meeting notes support initial Q&A completion. Add links; recurring unresolved decisions remain separate tasks. |
| 1.7 / #7 | Done / Chris | Import manifest records schedule source; live project exists. Link authoritative workbook and this review; distinguish initial schedule creation from maintenance. |
| 1.8 / #8 | Done / Joe | Budget not present in inspected repo. Locate and link actual budget before treating completion as independently verified. |
| 1.9 / #9 | Done / Tyler | Standalone DVP not present in inspected repo. Locate it and link V-01–V-17 definitions; new reference-validation report supplements rather than replaces it. |

## Concept and prototype tasks

| ID / issue | Live status / owner | Evidence and recommended update |
| --- | --- | --- |
| 2.1 / #10 | Done / Joe | Download jobs/setup exist. Keep initial access task complete; full production precompute is separate and not validated by this status. |
| 2.2 / #11 | Done / Chris | Synthetic pipeline and results exist. Add evidence links; keep Done. |
| 2.3 / #12 | In Progress / Chris | Mask prototype and tests exist; October 13 exports passed value/mask/CRS/transform readback. Recommend Done for prototype scope, subject to DVP criteria. Multi-tile user processing remains separate production work. Preserve planned October 12 final-week anchor; record observed evidence date separately. |
| 2.4 / #13 | Todo / Tyler | FDL/LDS and boundary received and inspected October 13; author PC1 absent. Recommend In Progress for original combined scope. Alternatively split completed data intake from unresolved PC1/provenance follow-up; do not call the original full deliverable Done. Preserve October 5 promised week as baseline; actual receipt date is not established by inspection date. |
| 2.5 / #14 | In Progress / Joe | Reference equivalence test runs starter on a synthetic season; archived report records team implementation on real seasons. Clarify whether V-04 requires original starter on real daily data. Synthetic execution demonstrated; real original-script execution not established. Keep In Progress until criterion checked; propose review in week of October 12. |
| 2.6 / #15 | Todo / Tyler | Updated full scripts not supplied. Keep Todo; October 16 is documented promised date, within existing October 12 week anchor. Track Tyler as intake coordinator; Woodruff is external provider. Do not treat the week anchor as an October 12 exact deadline. |
| 2.7 / #16 | Todo / Matthew | test_pca.py already has six size/scaling recovery cases and a sign test; added October 6. Recommend In Progress with scope changed to review/complete coverage against V-02, rather than build from scratch. Keep October 19 final-week anchor. Owner reviews existing work; assignee is not proof of code authorship. |
| 2.8 / #17 | Todo / Chris | October 13 reference-input PCA/SVD/scaling comparison completed. Recommend In Progress; explicitly separate completed numerical checks, team FDL comparison, unavailable author PC1 and unresolved D06. Remove false description that D06 is settled. Retain November 2 final-week anchor as planning target, with external dependency recorded. |
| 2.9 / #18 | Todo / Tyler | Boundary/grid feasibility and cross-state findings exist; HUC decision open. Scope remaining work as HUC comparison and sponsor decision, not starting boundary research again. Keep October 26 anchor. Status remains Todo absent evidence of work on that deliverable. |
| 2.10 / #19 | Todo / Tyler | No completed stack trade study found. Keep October 26 anchor; decision should precede detailed UI/mockup implementation. |
| 2.11 / #20 | Todo / Matthew | UI sketches not found. Keep October 19–26 anchors; use the required watershed/sensor/period/map/export workflow. |
| 2.12 / #21 | Todo / Chris | No snapshot slides found. Confirm course event date urgently: week of October 19 is next week. Add slide preparation scope, evidence and shared team contributions. |
| 2.13 / #22 | Todo / Chris | Review slides not found. Keep November 2–9 anchors pending course confirmation; require reviewed concepts and evidence of tradeoffs. |

## Detailed design and release tasks

| ID / issue | Live status / owner | Evidence and recommended scope |
| --- | --- | --- |
| 3.1 / #23 | Todo / Joe | Historical storage/runtime estimates exist in archive/realdata/README.md. Reuse as baseline; validate coverage of all offered watersheds, refresh, concurrency and actual storage. Keep October 19–26 anchors. |
| 3.2 / #24 | Todo / Chris | Earlier prototype timings exist, but no deployment-oriented benchmark. Define matrix sizes, machine, memory and timing method; keep October 26–November 2. |
| 3.3 / #25 | Todo / Matthew | Clickable mockup and sponsor feedback absent. Keep October 26–November 9; record feedback and resulting changes. |
| 3.4 / #26 | Todo / Joe | VIIRS samples exist, product/sensor strategy unresolved. Keep November 2–23 for full feasibility; propose initial product/grid feasibility check by week of October 26 so architecture does not assume MODIS-only support. |
| 3.5 / #27 | Todo / Tyler | RCDS/IWRRI hosting direction known, resource details unknown. Keep full November 2–30 review; propose early constraint discovery by week of October 26 before stack decision. External response timing unconfirmed. |
| 3.6 / #28 | Todo / Tyler | Current processing layout exists; no complete system/data-model design found. Keep November 9–23; define draft architecture as input to 4.1. |
| 3.7 / #29 | Todo / Matthew | Dependencies listed; licensing not settled. Keep November 9–16; review code/data/hosting dependencies, including new optional validation libraries. |
| 3.8 / #30 | Todo / Chris | Threshold 10 default is settled; sensitivity experiment absent. Define the effect on FDL/PCA separately from stretch cloud filling. Keep November 9–23. |
| 3.9 / #31 | Todo / Tyler | Server not started. Define request/output contracts, jobs, failures and export; keep November 16–30. |
| 3.10 / #32 | Todo / Tyler | Existing FDL tests cover numerous flags and edge cases. Scope as missing production coverage: alignment, insufficient/constant input, multi-tile handling and unavailable data, as justified by DVP. Coordinate with 2.7 to avoid duplicate tests. Keep November 16–30. |
| 4.1 / #33 | Todo / Chris | Define as integration/review of architecture, data flow and UI documents; 3.6 owns draft architecture/data model. Keep November 23–30. |
| 4.2 / #34 | Todo / Matthew | Requirements files are input, not complete BOM with vendors/costs. Include software versions/licenses, data products, hosting and costs. Keep November 23–30. |
| 4.3 / #35 | Todo / Tyler | Setup commands exist; deployment/build/operation plan absent. Keep November 23–30; include configuration, refresh, failures and recovery. |
| 4.4 / #36 | Todo / Joe | Consolidate final DVP/budget/schedule updates; requires linked originals from 1.7–1.9. Keep week of November 30. |
| 4.5 / #37 | Todo / Chris | Review evidence package not yet complete. Keep December 7 week anchor; exact course deadline remains unconfirmed. |

## Assignees and immediate priorities

Keep current owners unless the team agrees otherwise. Chris and Tyler each have
12 tasks and several overlapping November deliverables. Proposal: Matthew
reviews PCA coverage while Chris handles scientific comparison; Joe handles
matching daily-data acquisition/FDL execution while Tyler coordinates sponsor
inputs and constraints. These fit current assignments and do not establish
new commitments. Clarify Chris's 4.1 integration role versus Tyler's 3.6 draft.

During week of October 12: review 2.3 completion; update 2.4/2.7/2.8 evidence;
resolve V-04 scope; locate budget/DVP/workbook and confirm Snapshot date.
Add an explicit portfolio organization/index task: the seven required headings
and centralized deliverable links are not covered by the original 37 rows.
Suggested coordinator Tyler, with each document owner supplying their files;
owner/date require team agreement. No mass date shifts are justified yet.

## Sources and application cautions

- Live project and issue descriptions, inspected October 13.
- README.md, api/README.md and api/tests/ (tests inspected, not rerun for this review).
- decisions.md and woodruff-validation-2026-10-13.md with measured results.
- archive/realdata/README.md (historical experiment evidence, unchanged).
- document_list.md (external assignment links, contents not verified here).
- fall-2026-import.json (original source dates/owners, not current completion).

The historical fall-2026-review.md incorrectly says no import occurred; its
initial review text is not a live status report. Do not apply UpdateExisting
from the original manifest: it can overwrite newer evidence and board values.
Create a reviewed update manifest if applying changes, and preserve import keys.
Exact completion dates and new owner commitments must not be invented.
