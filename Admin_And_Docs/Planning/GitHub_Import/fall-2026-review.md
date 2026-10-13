# Fall 2026 GitHub import review

37 proposed issues for Snow-Visualization, added to organization Project 1 (Phase 1 Fall 2026). No GitHub changes have been made.

Source: Snow-Viz_Project_Schedule.xlsx, Schedule, updated October 6, 2026. Scope: phases 1–4, rows 9–48 excluding phase headings.

## Review rules

- Dates below are Monday anchors for the first and final chart weeks, not exact deadlines. The import manifest leaves Target date blank until confirmed.
- Status is proposed from the legend: all green = Done; green and blue = In Progress; blue or orange milestone = Todo. No issue will be closed based on color without review.
- Grey university-break cells are excluded. Original durations remain text; bar length does not overwrite them.
- Phase headings become a Phase field, not extra issues. Fall includes five milestone tasks; the other two workbook milestones are in Spring.
- User-provided assignee mappings are retained; GitHub account existence and assignability have not been verified.
- Project write access, field IDs, and Status option IDs still need verification before importing.

## Task list

| ID | Task | Assignee | Duration | Start week | Final week | Proposed status | Review |
|---|---|---|---|---|---|---|---|
| 1.1 | Team assignment, team contract | @tylero07 | 2 wks | 2026-09-07 | 2026-09-14 | Done | — |
| 1.2 | Sponsor kickoff meeting | @tylero07 | Milestone | 2026-09-14 | 2026-09-14 | Done | Diamond identifies a week, not an exact event date. |
| 1.3 | Literature review (2019 WRR, 2026 RSASE & Hydrological Processes papers) | @blahblah-blah2305 | 4 wks | 2026-09-14 | 2026-10-05 | In Progress | — |
| 1.4 | Value Proposition assignment | @blahblah-blah2305 | 1 wk | 2026-09-14 | 2026-09-21 | Done | Duration says 1 wk; chart marks 2 weeks. |
| 1.5 | Product Requirements Document | @cbalesohay | 1 wk | 2026-09-14 | 2026-09-21 | Done | Duration says 1 wk; chart marks 2 weeks. |
| 1.6 | Sponsor question list, decision register, Q&A meeting | @cbalesohay | 2 wks | 2026-09-14 | 2026-09-28 | Done | Duration says 2 wks; chart marks 3 weeks. |
| 1.7 | Project Schedule (this workbook) | @cbalesohay | 5 days | 2026-10-05 | 2026-10-05 | Done | — |
| 1.8 | Project Budget | @j-davitt | 5 days | 2026-10-05 | 2026-10-05 | Done | — |
| 1.9 | Design Validation Plan | @tylero07 | 5 days | 2026-10-05 | 2026-10-05 | Done | — |
| 2.1 | NASA Earthdata access and download scripts (DVP V-06) | @j-davitt | 2 wks | 2026-09-14 | 2026-09-28 | Done | Duration says 2 wks; chart marks 3 weeks. |
| 2.2 | Rapid prototype: synthetic-data PCA pipeline (V-01, V-03) | @cbalesohay | 2 wks | 2026-09-14 | 2026-09-28 | Done | Duration says 2 wks; chart marks 3 weeks. |
| 2.3 | Rapid prototype: watershed mask + GeoTIFF export (V-07, V-08) | @cbalesohay | 3 wks | 2026-09-21 | 2026-10-12 | In Progress | Duration says 3 wks; chart marks 4 weeks. |
| 2.4 | Sponsor deliverable: Upper Snake boundary + FDL/PC1 reference rasters | @tylero07 | Milestone | 2026-10-05 | 2026-10-05 | Todo | Diamond identifies a week, not an exact event date. Sponsor reference rasters were promised for 2026-10-05; receipt is not confirmed by this schedule. |
| 2.5 | Run FDL starter script on one melt season (V-04) | @j-davitt | 2 wks | 2026-10-05 | 2026-10-12 | In Progress | — |
| 2.6 | Sponsor deliverable: updated FDL → PCA → cloud-removal scripts | @tylero07 | Milestone | 2026-10-12 | 2026-10-12 | Todo | Diamond identifies a week, not an exact event date. Decision register records updated scripts promised for 2026-10-16; chart only identifies week of 2026-10-12. |
| 2.7 | PCA unit test suite (V-02) | @blahblah-blah2305 | 2 wks | 2026-10-12 | 2026-10-19 | Todo | — |
| 2.8 | Reproduce reference rasters; decide PCA scaling D06 (V-05) | @cbalesohay | 4 wks | 2026-10-12 | 2026-11-02 | Todo | D06 already establishes raw FDL PCA without column standardization; remaining sign and masking conventions need documentation. |
| 2.9 | HUC level analysis; decide D08 with sponsor (V-11) | @tylero07 | 3 wks | 2026-10-12 | 2026-10-26 | Todo | — |
| 2.10 | Web stack trade study (2–3 concepts) | @tylero07 | 3 wks | 2026-10-12 | 2026-10-26 | Todo | — |
| 2.11 | UI concept sketches | @blahblah-blah2305 | 2 wks | 2026-10-19 | 2026-10-26 | Todo | — |
| 2.12 | Snapshot Day – Fall (TBC) | @cbalesohay | Milestone | 2026-10-19 | 2026-10-19 | Todo | Tentative course date; confirm against CS 4800 calendar. Diamond identifies a week, not an exact event date. |
| 2.13 | Concept Design Review prep and presentation (TBC) | @cbalesohay | 2 wks | 2026-11-02 | 2026-11-09 | Todo | Tentative course date; confirm against CS 4800 calendar. |
| 3.1 | Storage & precompute sizing calculation (V-09) | @j-davitt | 2 wks | 2026-10-19 | 2026-10-26 | Todo | — |
| 3.2 | PCA runtime benchmark (V-10) | @cbalesohay | 2 wks | 2026-10-26 | 2026-11-02 | Todo | — |
| 3.3 | Clickable mockup + sponsor walkthrough (V-13) | @blahblah-blah2305 | 3 wks | 2026-10-26 | 2026-11-09 | Todo | — |
| 3.4 | VIIRS feasibility & MODIS agreement; decide D02/D03 (V-12) | @j-davitt | 3 wks | 2026-11-02 | 2026-11-23 | Todo | Duration says 3 wks; chart marks 4 weeks. D02 is partly answered: MOD10A1F v61 for FDL and MOD10A1 v61 for cloud removal. VIIRS and D03 remain unresolved. |
| 3.5 | Hosting architecture review with RCDS/IWRRI (V-15) | @tylero07 | 5 wks | 2026-11-02 | 2026-11-30 | Todo | — |
| 3.6 | System architecture & data model document | @tylero07 | 2 wks | 2026-11-09 | 2026-11-23 | Todo | Duration says 2 wks; chart marks 3 weeks. |
| 3.7 | Dependency & license audit; choose license (V-14) | @blahblah-blah2305 | 2 wks | 2026-11-09 | 2026-11-16 | Todo | — |
| 3.8 | NDSI threshold sensitivity (V-16) | @cbalesohay | 2 wks | 2026-11-09 | 2026-11-23 | Todo | Duration says 2 wks; chart marks 3 weeks. |
| 3.9 | API specification | @tylero07 | 3 wks | 2026-11-16 | 2026-11-30 | Todo | — |
| 3.10 | Edge-case unit tests (V-17) | @tylero07 | 3 wks | 2026-11-16 | 2026-11-30 | Todo | — |
| 4.1 | Design document (architecture, data flow, UI) – "drawings" | @cbalesohay | 2 wks | 2026-11-23 | 2026-11-30 | Todo | — |
| 4.2 | Software bill of materials (dependencies, data products, hosting) | @blahblah-blah2305 | 2 wks | 2026-11-23 | 2026-11-30 | Todo | — |
| 4.3 | Build & deployment plan – "manufacturing plan" | @tylero07 | 2 wks | 2026-11-23 | 2026-11-30 | Todo | — |
| 4.4 | Update DVP, budget and schedule for ERR | @j-davitt | 5 days | 2026-11-30 | 2026-11-30 | Todo | — |
| 4.5 | Engineering Release Review (TBC) | @cbalesohay | Milestone | 2026-12-07 | 2026-12-07 | Todo | Tentative course date; confirm against CS 4800 calendar. Diamond identifies a week, not an exact event date. |

## Import plan

Use the adjacent JSON manifest as the reviewed input. Each record contains the proposed issue body, original source row, stable import key, and placeholders for the issue URL and Project item ID.

After authorization: verify account access and assignee eligibility; read Project fields and existing issues; create Phase, Duration, Schedule ID, Start date and Target date fields as needed; create two representative issues first; inspect the result; then finish the import. Preserve existing Status options by mapping proposals to their actual option IDs.

Check each stable import key in existing issue bodies and the saved import log before creating an issue. Record the issue URL immediately after creation and resume Project field updates separately on retry. Do not use task-title matching alone.

Keep GitHub issue state and Project Status distinct. The 10 Done proposals require confirmation before closing issues. All date and status proposals are based on the source workbook, not current repository completion.

Repository context notes come from Admin_And_Docs/Planning/decisions.md. Task titles remain faithful to the schedule, including choices that have since been partly answered. No technical decision is resolved by this import.
