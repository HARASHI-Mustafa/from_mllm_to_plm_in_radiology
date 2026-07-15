# Frontend

React + Vite frontend for `MLLM - PLM Workflow`.

The frontend uploads a chest X-ray image to the FastAPI backend, displays the returned analysis result, and provides export actions for the latest backend artifacts.

## Requirements

- Node.js
- npm
- Running FastAPI backend, usually at `http://localhost:8000`

## Install

```powershell
cd frontend
npm install
```

## Development Server

```powershell
cd frontend
npm run dev
```

The Vite dev server usually runs at:

```text
http://127.0.0.1:5173/
```

## Production Build

```powershell
cd frontend
npm run build
```

Build output is written to `frontend/dist/`, which is ignored by Git.

## Environment Variables

By default, the app calls:

```text
http://localhost:8000
```

Override the API base URL before starting Vite:

```powershell
$env:VITE_API_BASE_URL="http://localhost:8000"
npm run dev
```

## Application Layout

- `Header`: application title and decision-support-only badge.
- `UploadPanel`: CXR image upload workspace and image preview.
- `AnalysisControl`: workflow progress, run analysis button, and reset button.
- `CaseSummary`: fused case-level summary from PLM output.
- `GeneratedReport`: CheXagent Findings and Impression display.
- `StructuredFindingsTable`: 14-label structured finding table with states, confidence, probabilities, and source.
- `DecisionSupport`: review priority, rationale, and safety note.
- `ExportButtons`: JSON, CSV, Markdown, generated report TXT, and copy-summary actions.

## Export Features

Export buttons prefer backend endpoints:

- `/api/exports/json`
- `/api/exports/csv`
- `/api/exports/markdown`
- `/api/exports/generated-report`

If the backend export endpoint is unavailable, the frontend falls back to static demo files in `public/mock/`.

## Static Demo Assets

The frontend keeps a small demo image and mock artifacts under:

```text
frontend/public/mock/
```

These files support frontend fallback exports and local UI demonstrations.

## Safety Disclaimer

The interface is for a research decision-support prototype. It is not a diagnostic medical device and does not replace clinical review.
