# Snow Cover

**Web-Based Satellite-Observed Mountain Snow-Cover Visualization Tool**  
University of Idaho · Capstone Project · 2026–2027

Snow Cover is a planned web application for exploring recurring patterns of mountain snowmelt in Idaho. Users will select a watershed, satellite sensor, and time period; the tool will retrieve satellite snow-cover observations, calculate the spatial sequence of snowmelt across years, display the result on a map, and provide a georeferenced image for download. [1, 2]

The project brings the research of Craig D. Woodruff and Russell J. Qualls into a tool that water managers and other users can operate without writing their own processing code. Mountain snowmelt is a major source of Idaho's water supply, making snow-cover information valuable for water management and drought assessment. [1, 3]

**Status:** This README describes the requirements and design direction documented through September 17, 2026. The supplied materials do not establish which features are implemented or provide a verified installation procedure or deployment URL.

## Project scope

The core deliverable is an accessible web tool that generates and visualizes the **interannually recurring snowmelt pattern**: the relative order in which locations tend to become snow-free during spring melt. [1–3]

### Planned capabilities

- Select an Idaho watershed from a map, with map or list selection discussed in the project meeting.
- Choose MODIS or VIIRS satellite observations and a time period.
- Retrieve multiple years of daily snow-cover data from the National Snow and Ice Data Center (NSIDC).
- Process those observations into a recurring snowmelt pattern.
- Display the pattern over a map and download a georeferenced raster, such as a GeoTIFF.
- Host the application on a publicly accessible platform selected with the sponsor.
- Refine usability through end-user feedback.
- Use Python or another open-source language and structure the work for future expansion beyond Idaho. [1, 2, 4]

### Stretch goal

Allow a user to select a day and estimate snow cover beneath clouds using the recurring melt pattern and the visible portion of that day's satellite image. The project brief identifies this as an extension if time permits. [1, 4]

### Intended users

The project materials identify potential users including the Idaho Department of Water Resources, Idaho Office of Emergency Management, NRCS SNOTEL, U.S. Army Corps of Engineers, Idaho Power, National Weather Service, NASA, and the Pacific Northwest Drought Early Warning System committee. These are intended audiences or interested organizations; the documents do not establish them as repository contributors or formal project partners. [1, 2]

## Scientific approach

The method is based on Woodruff and Qualls (2019), which uses **principal component analysis (PCA)** to extract the snowmelt pattern shared across multiple years of satellite observations. [3]

1. **Prepare daily observations.** Classify valid snow observations using a Normalized Difference Snow Index (NDSI) threshold, while distinguishing cloud-obscured and missing observations.
2. **Identify annual melt timing.** Determine the first day land is observed at each pixel during seasonal melt. The paper calls this **FDL**; the meeting summary uses **FTL** for the same concept. The paper also derives the last day of snow (LDS) to examine uncertainty from clouds.
3. **Build a pixels-by-years matrix.** Flatten each annual melt-timing raster into a column, preserving the same pixel order and geographic alignment across years.
4. **Extract the recurring pattern.** Apply PCA and reshape the first principal component (PC1) scores into a georeferenced image. The meeting proposes standardizing each year's column before PCA.
5. **Visualize relative melt timing.** Under the sources' display convention, darker values indicate earlier melt and lighter values indicate later melt. The resulting pattern describes relative melt timing, rather than an exact calendar date or snow-water volume.
6. **Optionally fill cloud gaps.** Fit a threshold on the recurring pattern to the visible snow and land in a selected day's image, then use it to estimate snow coverage in obscured areas. The paper selects this threshold by minimizing visible-pixel error. [2–4]

### Evidence and limitations

The published study developed its model with 17 years of MODIS observations (2000–2016) in the Upper Snake River Basin and evaluated it against independent observations from 2017–2018. PC1 explained **85% of the variance**, and reported spatial agreement with satellite snow-cover images ranged from **84.9% to 97.5%**. These are results from the research study, not measured performance of this application. [3]

The meeting summary mentions approximately 97% explained variance; that differs from the paper's 85% result and should not be treated as a confirmed benchmark. Cloud-gap estimates depend on the visible observations, with better constraints when some of the snow–land boundary is visible. Persistent classification errors, cloud cover, and differences in seasonal snow coverage can affect results. [3, 4]

## Data and processing design

| Area | Documented direction |
| --- | --- |
| Satellite data | MODIS and VIIRS are required sensor choices; NSIDC is the specified retrieval source. [1, 2] |
| Research baseline | The paper used Terra MODIS `MOD10A1`, Collection 6, daily 500 m NDSI snow-cover data. This identifies the historical study product, not a finalized application product version. [3] |
| Precomputation | Precompute and store annual first-land rasters statewide for each selected NDSI threshold, before clipping to individual watersheds. [4] |
| User processing | Reuse the stored layers for watershed-specific processing, pattern generation, display, and export. [4] |
| Storage and hosting | Sponsor coordination is pending for map data, application hosting, and data storage. [4] |

This design keeps the expensive scan through daily imagery out of individual user requests. The meeting describes roughly four MODIS tiles covering Idaho; the final data coverage and processing configuration remain to be established. [4]

## Development priorities

The September 15, 2026 meeting identifies an initial task for the student team: prototype the PCA pipeline with synthetic data while awaiting sample datasets. The proposed exercise is to create a pixels-by-years matrix, standardize the columns, compute PCA, extract PC1, and reconstruct the image layout. [4]

Dr. Qualls is to provide research references and sample data and coordinate access to state and watershed maps and hosting information. No due dates were set in that meeting. [4]

Decisions still open in the supplied materials include:

- The NDSI threshold and whether users may choose it. The meeting's value of 10 was an example, not an agreed setting.
- How to handle MODIS and VIIRS together while retaining the longer MODIS record.
- Hosting and storage arrangements.
- How the existing first-land algorithm handles snowfall after initial melt-out.

The materials do not specify application dependencies, a frontend or backend framework, environment variables, or run commands. Setup instructions should be added once they can be verified against the implementation.

## Team and acknowledgments

### Student team

The September 15 meeting summary identifies the following student participants: [4]

- **Tyler**
- **Chris**
- **Joe**
- **Matthew**

Only first names are supplied. The summary warns that transcription quality is poor and names may be approximate; surnames, GitHub handles, individual responsibilities, and a complete contributor roster are not established by these documents.

### Project sponsor

**Dr. Russell Qualls** — University of Idaho, Biological Engineering; project sponsor and scientific guidance. The presentation lists [rqualls@uidaho.edu](mailto:rqualls@uidaho.edu) as the sponsor contact. The research paper identifies him as **Russell J. Qualls**. [2–4]

### Research foundation

**Craig D. Woodruff** and **Russell J. Qualls** authored the 2019 paper underlying the PCA snowmelt method. Their credit here recognizes the scientific foundation; the supplied materials do not establish Craig D. Woodruff as a contributor to this repository. [3]

## Source documents

This README is grounded in the four supplied project documents. The numbered references distinguish project requirements, meeting decisions, and published research.

1. **Project brief:** *Web-Based Satellite-Observed Mountain Snow-Cover Visualization Tool*. File: `51-UI CS-BE Qualls-Satellite Data Snow Visualization Web Tool.docx`. Defines scope, design requirements, intended users, and the optional cloud-gap-filling extension.
2. **Project presentation:** *Web-Based Satellite-Observed Mountain Snow-Cover Visualization Tool*, University of Idaho Capstone Project, 2026–27. File: `Snow Cover Project Presentation.pptx`. Identifies the sponsor, workflow, user options, and processing responsibilities.
3. **Research paper:** Woodruff, C. D., & Qualls, R. J. (2019). *Recurrent snowmelt pattern synthesis using principal component analysis of multiyear remotely sensed snow cover*. **Water Resources Research, 55**, 6869–6885. [https://doi.org/10.1029/2018WR024546](https://doi.org/10.1029/2018WR024546). File: `Woodruff_Qualls_2019_WRR_Recurrent Snowmelt Pattern_PCA Model (1).pdf`.
4. **Meeting summary:** *Snowmelt Pattern Analysis Using MODIS Data*. Meeting held September 15, 2026; summary dated September 17, 2026. Repository file: `Admin_And_Docs/Meeting_Notes/1_Meeting_9_15_26.docx` (original upload: `Snowmelt_Meeting_Summary.docx`). Records student names, the proposed processing design, action items, and unresolved questions; includes a transcription-quality caveat.

## License

The supplied project documents do not specify a software license. The repository's license must be established separately; the research paper's publication rights do not define the software's license.
