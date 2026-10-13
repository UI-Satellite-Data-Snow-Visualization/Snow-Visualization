# Schedule API importer

Uses Python 3.10+ and the standard library; no packages or GitHub CLI are needed.
`Import-Schedule.ps1` finds the Codex bundled Python on this Windows computer,
or an installed `python` command. Run it from the same PowerShell window where
`GH_TOKEN` is set. It never prints or saves the token.

## Preview the existing Fall import

```powershell
Set-Location 'C:\Users\ossoc\OneDrive\Documents\College\College\Capstone\main_repo'
& '.\Admin_And_Docs\Planning\GitHub_Import\Import-Schedule.ps1'
```

The default is read-only. All 37 Fall issues should say `SKIP existing`.
It checks the destination title, fields, options, assignees, duplicate markers,
and recorded issue URLs before allowing any writes. Read access does not prove
token write permissions. Token: organization Projects read/write and repository
Issues read/write; the account itself also needs write access.

## Import a future reviewed schedule

Prepare a separate JSON manifest using the Fall file as a schema example.
Use the new Project number and exact title, new task rows and unique import keys.
Do not copy Fall issue URLs into new tasks. Create the destination Project and its
fields/options first. The script does not create Projects, fields or options.

```powershell
& '.\Admin_And_Docs\Planning\GitHub_Import\Import-Schedule.ps1' -Manifest '.\path\spring-import.json'
# After reviewing the preview:
& '.\Admin_And_Docs\Planning\GitHub_Import\Import-Schedule.ps1' -Manifest '.\path\spring-import.json' -Apply
```

Each manifest specifies `repository`, `project_number`, `project_title`, and
`items`. Each item requires `schedule_id`, `import_key`, `title`, `body`,
`assignee`, `duration`, and `status_proposal`. Optional dates are `start_week`,
`final_week`, and `suggested_target_date` (YYYY-MM-DD or null).
Set `project_phase` per item, or a manifest `phase_options` object mapping the
prefix before the task ID's dot to an exact Phase option name. Fall defaults
are prefixes 1–4. Source notes and review flags must be included in `body`.

| JSON value | GitHub destination | Type |
| --- | --- | --- |
| title / body | Issue title / description | Issue properties |
| assignee | Issue assignee | GitHub login |
| status_proposal | Status | Single select |
| project_phase or phase_options | Phase | Single select |
| duration | Duration | Text |
| schedule_id | Schedule ID | Text |
| start_week | Start week | Date |
| final_week | Final week | Date |
| suggested_target_date | Target date | Date |

Week anchors are not exact deadlines. Null target dates remain blank. Preserve
uncertainties in descriptions. The importer never intentionally changes issue
open/closed state, but GitHub Project workflows may do so when Status changes.
Fall's Auto-close issue workflow was disabled during the initial import.
Review destination workflows before applying another import.

## Resume or deliberately update

Issues are identified by an exact HTML import marker in the body, including
closed issues. A pagination scan checks all repository issues, rather than a
search index. Existing issues are skipped by default, preserving subsequent
team edits. An interrupted run can leave a created issue without complete
Project fields: preview with `-UpdateExisting`, then apply that reviewed plan.

`-UpdateExisting` replaces the matching issue's title, description, sole
assignee, and mapped Project fields, including clearing fields whose manifest
value is null. It can overwrite newer team progress; use a current reviewed
manifest. Matching values generate no mutation. No deletion or closing occurs.

Apply writes a sibling `.results.json` checkpoint after each issue creation and
Project attachment. The original manifest remains unchanged. If a write times
out, it is not retried automatically; preview again to discover any completed
creation, then resume. A final API read verifies changed values. Project state
can still be affected asynchronously by workflows. Do not run two importers
concurrently: duplicate prevention is not an atomic server-side constraint.

Offline validation: `-Offline` checks JSON without a token or GitHub connection.
Tests: `python -m unittest discover -s Admin_And_Docs/Planning/GitHub_Import -p 'test_*.py'`.

API reference: https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects
