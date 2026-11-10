# Snow Visualization client

React + TypeScript + Vite. A local form for selecting stored MODIS data and
running watershed PCA. No map or browser-triggered satellite downloads yet.

## Run locally

Start FastAPI in one terminal, from the repository root:

```bash
cd api
source .venv/bin/activate
python -m uvicorn server.main:app --reload
```

Start the frontend in another terminal:

```bash
cd client
nvm use 24
npm install  # first setup, or after dependency changes
npm run dev
```

Open the URL Vite prints (normally http://localhost:5173). Node 24 is the
local development baseline. `npm run build` checks TypeScript and builds `dist/`.

Vite proxies `/api/*` to `http://127.0.0.1:8000/*`, including PNG and GeoTIFF
responses. This proxy applies to the development server. Production hosting
must configure an equivalent reverse proxy; `vite preview` alone does not
provide the API. No CORS changes or browser credentials are needed locally.

## Workflow

Choose a watershed, a stored threshold, at least two years, and PCA scaling.
Click Run PCA to see variance explained, retained pixel counts, a plain PC1
preview and a GeoTIFF download. Changing settings clears the previous result.

The page checks availability at thresholds 10, 20, 30, 40 and 50 and only offers
those with stored years. Other thresholds are not exposed by this initial UI.
Availability comes from the API, not hard-coded year ranges. Covariance is the
default; correlation remains available because scientific decision D06 is open.
Results describe relative melt timing, not dates or water volume.

Missing data is reported without starting a download. Import/precompute it with
the Python jobs, restart the API to clear cached PCA results, and refresh the
page. Preview and download links also expire when the API cache is cleared or
the result is evicted; rerun PCA to recreate them. VIIRS ingestion remains pending.
