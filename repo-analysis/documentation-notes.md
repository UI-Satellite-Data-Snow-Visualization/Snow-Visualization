# Documentation notes

Checked September 22, 2026 at local commit `60ee01f5119bfa828e8ce2684f926ed6ab7f579b`.

## DeepWiki status

[Repository wiki](https://deepwiki.com/UI-Satellite-Data-Snow-Visualization/Snow-Visualization): HTTP 200, but the retrieved page contained “Loading...” and no readable wiki chapters. Indexing status is **unverified**; no indexing request was submitted because browser control returned “No browser is available”. The following notes summarize local repository documentation, not DeepWiki output.

## Project and proposed architecture

[README](../README.md) describes a planned Idaho snowmelt visualization web tool: select a watershed, sensor and years; process satellite observations; map a recurring relative melt-timing pattern; export a georeferenced raster. Daily cloud-gap filling is a stretch goal.

The meeting-derived direction documented in the README is statewide annual first-land precomputation followed by watershed clipping. PCA inputs use pixels as rows and years as columns; spatial scores are reshaped to the raster. Column standardization is a meeting proposal. Masks, raster alignment, pixel order and sign orientation must be explicit. No frontend, backend, storage or hosting implementation exists in the tracked tree.

## Entry points and setup

There are no executable application entry points. Start reading [README.md](../README.md), [project plan](../Admin_And_Docs/Planning/project-plan.md), [decision register](../Admin_And_Docs/Planning/decisions.md), and [PCA prototype plan](../Admin_And_Docs/Planning/pca-prototype-plan.md). Planning proposals are not agreed sponsor requirements.

No application dependencies, verified installation command, build command or test runner are present. The PCA plan proposes synthetic reconstruction, orientation, mask and alignment checks; those checks have not been implemented or run.

## GitMCP verification questions — local fallback answers

These answers are based on the local tree, **not successful GitMCP queries**.

1. **What does this project do?** Plans a web tool for mapping recurring mountain snowmelt patterns from multiyear satellite observations. Source: [README](../README.md).
2. **Where are its main entry points?** No executable entry points exist; the documentation entry point is [README](../README.md).
3. **How do I run its tests?** No test suite or verified test command exists. Proposed checks are in the [PCA prototype plan](../Admin_And_Docs/Planning/pca-prototype-plan.md).
