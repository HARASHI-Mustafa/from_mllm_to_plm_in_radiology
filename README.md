# MLLM - PLM Workflow

Repository: `from_mllm_to_plm_in_radiology`

## Project Overview

`MLLM - PLM Workflow` is a local research prototype for chest X-ray report generation, predictive language model extraction, and decision-support review. It connects a multimodal large language model (MLLM) report-generation stage with a PLM/RadBERT structured extraction stage, then presents the output in a React review interface.

## Safety Disclaimer

This project is a research decision-support prototype. It is not a diagnostic medical device, is not clinically validated for deployment, and does not replace qualified clinical review. Outputs must be reviewed by appropriate clinical professionals before any clinical use.

## Objectives

- Generate radiology-style Findings and Impression text from a chest X-ray image.
- Extract 14 structured finding labels from generated report text with PLM/RadBERT models.
- Fuse section-level extraction into a reviewable decision-support output.
- Provide a frontend workflow for image upload, report review, structured findings, review rationale, and exports.
- Keep the MLLM runtime isolated from the FastAPI/PLM runtime to avoid dependency conflicts.

## Architecture

- `frontend/`: React + Vite application for upload, analysis control, generated report display, structured findings, decision-support summary, and exports.
- `backend/`: FastAPI API, pipeline orchestration, PLM services, MLLM worker launch, runtime outputs, and export endpoints.
- `backend/mllm_worker/`: standalone CheXagent worker scripts that run in a separate Python environment.
- `sources/`: local demo images, precomputed demo outputs, PLM inference modules, local model folders, and Hugging Face cache location.
- `docs/`: supporting application notes, demo checklist, and report-oriented documentation.

## Pipeline Diagram

```text
Chest X-ray image
  -> CheXagent MLLM worker
  -> generated Findings + Impression
  -> PLM/RadBERT structured extraction
  -> fusion and consistency checks
  -> decision-support summary
  -> React review UI and exports
```

## Features

- Image upload for JPG, JPEG, and PNG chest X-ray inputs.
- Real MLLM-to-PLM analysis through `/api/analyze`.
- Mock mode for deterministic demos without model loading.
- PLM-from-precomputed-report mode for testing PLM extraction independently.
- Generated Findings and Impression panels.
- 14-label structured findings table with state, confidence, probabilities, and source.
- Decision-support summary with review priority and rationale.
- JSON, CSV, Markdown, generated report TXT, and copy-summary export actions.

## Technology Stack

- Frontend: React, Vite, JavaScript, CSS.
- Backend: FastAPI, Pydantic, Uvicorn.
- Model runtime: PyTorch, Transformers, CheXagent worker environment, PLM/RadBERT inference modules.
- Local artifacts: JSON, CSV, Markdown, and TXT exports.

## Repository Structure

```text
from_mllm_to_plm_in_radiology/
|-- backend/
|   |-- app/
|   |-- mllm_worker/
|   |-- outputs/
|   |-- requirements.txt
|   |-- requirements-inference.txt
|   |-- requirements-mllm.txt
|   |-- start_backend.ps1
|   `-- README.md
|-- frontend/
|   |-- public/
|   |-- src/
|   |-- package.json
|   |-- vite.config.js
|   `-- README.md
|-- sources/
|   |-- input_images/
|   |-- outputs/
|   |-- plm_inference/
|   |-- plm_models/
|   |-- mllm_models/
|   |-- hf_cache/
|   `-- README.md
|-- docs/
|-- .gitignore
`-- README.md
```

Large model folders, Hugging Face caches, virtual environments, uploads, and runtime outputs are intentionally ignored by Git.

## Installation

Clone the repository and install the backend and frontend dependencies separately. The backend uses two Python environments:

1. Main FastAPI/PLM environment: `backend/.venv`
2. Isolated CheXagent/MLLM worker environment: `backend/.venv-mllm`

## Backend Setup

Main backend and PLM environment:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-inference.txt
```

Linux/macOS equivalent:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-inference.txt
```

## MLLM Worker Environment

CheXagent dependencies must be installed in a separate environment:

```powershell
cd backend
python -m venv .venv-mllm
.\.venv-mllm\Scripts\Activate.ps1
pip install -r requirements-mllm.txt
```

Do not install `requirements-mllm.txt` into the main backend `.venv`. The MLLM worker has pinned dependencies that should remain isolated from FastAPI and PLM/RadBERT dependencies.

## Model Placement

Required local model folders:

```text
sources/mllm_models/chexagent_findings/
sources/mllm_models/chexagent_impression/
sources/plm_models/radbert_findings_model/
sources/plm_models/radbert_impression_model/
```

See [sources/README.md](sources/README.md) for the expected directory layout and model file notes.

## Running the Application

Start the backend in real mode from `backend/`:

```powershell
.\.venv\Scripts\Activate.ps1
$env:RADIOLOGY_PIPELINE_MODE="real"
$env:RADIOLOGY_MLLM_PYTHON=(Resolve-Path ".\.venv-mllm\Scripts\python.exe").Path
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The repository also includes a Windows helper:

```powershell
cd backend
.\start_backend.ps1
```

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000`. Override the API base URL when needed:

```powershell
$env:VITE_API_BASE_URL="http://localhost:8000"
```

## Pipeline Modes

Set `RADIOLOGY_PIPELINE_MODE` before starting the backend:

- `real`: runs CheXagent Findings and Impression generation in the isolated worker, then runs PLM/RadBERT extraction.
- `plm_from_precomputed_report`: uses precomputed Findings and Impression text, then runs real PLM/RadBERT extraction.
- `mock`: returns precomputed demo JSON from `sources/outputs/final_whole_system_demo/`.

### Real Pipeline

Use `RADIOLOGY_PIPELINE_MODE=real` when local CheXagent and PLM/RadBERT model files are ready and CUDA is available for the MLLM worker.

### Mock Mode

Use `RADIOLOGY_PIPELINE_MODE=mock` for deterministic demos that do not require local model files.

## Demo Instructions

Use the included demo image:

```text
sources/input_images/example_cxr.jpg
```

Recommended demo flow:

1. Start the backend in `real` mode, or use `plm_from_precomputed_report` / `mock` as fallbacks.
2. Start the frontend with `npm run dev`.
3. Upload `sources/input_images/example_cxr.jpg`.
4. Run analysis.
5. Review the generated report, structured findings, decision-support summary, and exports.

See [docs/demo_checklist.md](docs/demo_checklist.md) for a more detailed demo checklist.

## Exports

Real `/api/analyze` runs save latest artifacts under:

```text
backend/outputs/latest/
```

Timestamped run copies are saved under:

```text
backend/outputs/runs/
```

These runtime outputs are ignored by Git. Export endpoints fall back to precomputed demo artifacts when latest runtime outputs are unavailable.

## API Overview

- `GET /api/health`
- `GET /api/pipeline/status`
- `GET /api/plm/status`
- `GET /api/mllm/status`
- `POST /api/plm/extract`
- `POST /api/mllm/generate/findings`
- `POST /api/mllm/generate/impression`
- `POST /api/mllm/generate/report`
- `POST /api/analyze`
- `GET /api/exports/json`
- `GET /api/exports/csv`
- `GET /api/exports/markdown`
- `GET /api/exports/generated-report`

See [backend/README.md](backend/README.md) for endpoint details and example calls.

## Screenshots

Screenshots are not included yet. Suggested screenshots before publication:

- Empty upload workspace.
- Uploaded image preview.
- Running analysis state.
- Completed generated report.
- Structured findings table.
- Decision-support summary and export panel.

## Documentation

- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)
- [Sources README](sources/README.md)
- [Demo checklist](docs/demo_checklist.md)
- [Application summary](docs/final_application_summary.md)

## License

This repository contains only the application code. Pretrained model weights (CheXagent, RadBERT) are not distributed and remain subject to their respective licenses and terms of use.

## Future Work

- Add deployment documentation for a packaged local demo.
- Add optional job-based progress updates for long-running real-mode analysis.
- Add stronger evaluation and calibration reporting.
- Add batch-processing support.
- Add DICOM/PACS-oriented ingestion only after appropriate clinical and security review.

## Acknowledgements

This prototype builds on open-source Python, FastAPI, React, Vite, PyTorch, Transformers, and radiology language-model research tooling. Add model-specific citations and license notes before public release.
