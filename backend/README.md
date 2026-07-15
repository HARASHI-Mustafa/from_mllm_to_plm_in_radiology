# Backend

FastAPI backend for `MLLM - PLM Workflow`.

The backend exposes health, readiness, MLLM, PLM, analysis, and export endpoints. It intentionally keeps the CheXagent MLLM runtime in a separate worker environment so the main FastAPI/PLM environment can remain stable.

## Runtime Layout

- Main backend/PLM environment: `backend/.venv`
- Isolated MLLM worker environment: `backend/.venv-mllm`
- Worker scripts: `backend/mllm_worker/`
- Runtime uploads: `backend/uploads/`
- Latest exports: `backend/outputs/latest/`
- Timestamped run exports: `backend/outputs/runs/`

Runtime uploads and outputs are ignored by Git.

## Pipeline Modes

Set `RADIOLOGY_PIPELINE_MODE` before starting the backend:

- `real`: run CheXagent Findings and Impression generation in the isolated MLLM worker, then run PLM/RadBERT extraction.
- `plm_from_precomputed_report`: use precomputed Findings and Impression text, then run real PLM/RadBERT extraction.
- `mock`: return precomputed demo JSON and artifacts.

## Main Backend / PLM Environment

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-inference.txt
```

Linux/macOS:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-inference.txt
```

## Separate MLLM Worker Environment

Windows PowerShell:

```powershell
cd backend
python -m venv .venv-mllm
.\.venv-mllm\Scripts\Activate.ps1
pip install -r requirements-mllm.txt
```

Linux/macOS:

```bash
cd backend
python -m venv .venv-mllm
source .venv-mllm/bin/activate
pip install -r requirements-mllm.txt
```

Do not install `requirements-mllm.txt` into the main backend `.venv`. CheXagent and its pinned Transformers runtime must remain isolated from FastAPI and PLM/RadBERT dependencies.

## CUDA Requirements

Real mode is intended for a CUDA-capable environment. Before running a real analysis:

```powershell
nvidia-smi
python mllm_worker\check_environment.py
python mllm_worker\check_model_files.py
```

Generation should not be attempted until:

- `check_environment.py` exits `0`.
- `check_model_files.py` exits `0`.
- `GET /api/pipeline/status` reports `real_pipeline_ready: true`.

CPU fallback is disabled by default because it can be extremely slow. For debugging only:

```powershell
$env:RADIOLOGY_MLLM_ALLOW_CPU="true"
```

## Environment Variables

Common real-mode settings from `backend/`:

```powershell
$env:RADIOLOGY_PIPELINE_MODE="real"
$env:RADIOLOGY_MLLM_PYTHON=(Resolve-Path ".\.venv-mllm\Scripts\python.exe").Path
```

Fallback modes:

```powershell
$env:RADIOLOGY_PIPELINE_MODE="plm_from_precomputed_report"
$env:RADIOLOGY_PIPELINE_MODE="mock"
```

## Starting the Backend

Manual start:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:RADIOLOGY_PIPELINE_MODE="real"
$env:RADIOLOGY_MLLM_PYTHON=(Resolve-Path ".\.venv-mllm\Scripts\python.exe").Path
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Windows helper script:

```powershell
cd backend
.\start_backend.ps1
```

`start_backend.ps1` activates `backend/.venv`, sets `RADIOLOGY_PIPELINE_MODE=real`, points `RADIOLOGY_MLLM_PYTHON` to `backend/.venv-mllm/Scripts/python.exe`, and starts Uvicorn on port `8000`.

## Health and Readiness Endpoints

- `GET /api/health`: lightweight health check.
- `GET /api/pipeline/status`: pipeline mode, readiness, model file checks, CUDA status, and available modes.
- `GET /api/plm/status`: PLM dependency and model readiness.
- `GET /api/mllm/status`: MLLM worker environment and CheXagent model readiness.

## API Endpoints

- `POST /api/plm/extract`: run PLM/RadBERT extraction from Findings and Impression text.
- `POST /api/mllm/generate/findings`: generate Findings only through the worker.
- `POST /api/mllm/generate/impression`: generate Impression only through the worker.
- `POST /api/mllm/generate/report`: generate Findings, clean GPU memory, generate Impression, and clean GPU memory.
- `POST /api/analyze`: run the selected full pipeline mode for an uploaded CXR image.
- `GET /api/exports/json`: latest real output JSON if available, otherwise demo output JSON.
- `GET /api/exports/csv`: latest structured findings CSV if available, otherwise demo CSV.
- `GET /api/exports/markdown`: latest decision-support Markdown if available, otherwise demo Markdown.
- `GET /api/exports/generated-report`: latest generated report TXT if available, otherwise demo TXT.

## Example API Calls

Pipeline status:

```powershell
curl http://localhost:8000/api/pipeline/status
```

Analyze an image:

```powershell
curl -X POST http://localhost:8000/api/analyze -F "file=@../sources/input_images/example_cxr.jpg"
```

MLLM report generation only:

```powershell
curl -X POST http://localhost:8000/api/mllm/generate/report -F "file=@../sources/input_images/example_cxr.jpg"
```

PLM extraction only:

```powershell
curl -X POST http://localhost:8000/api/plm/extract `
  -H "Content-Type: application/json" `
  -d '{"findings":"Lungs and Airways: No focal consolidation.","impression":"No acute cardiopulmonary abnormality."}'
```

## Runtime Artifacts

Real `/api/analyze` calls save latest artifacts under:

```text
backend/outputs/latest/
```

Timestamped run copies are saved under:

```text
backend/outputs/runs/
```

These runtime outputs are ignored by Git.

## Safety Disclaimer

This backend powers a research decision-support prototype. It is not a diagnostic medical device and does not replace clinical review.
