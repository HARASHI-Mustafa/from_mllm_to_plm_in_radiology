# MLLM Worker

This folder contains helper scripts for the isolated CheXagent/MLLM Python environment used by `MLLM - PLM Workflow`.

Do not install `requirements-mllm.txt` into the main FastAPI/PLM environment. Create a separate environment instead:

```powershell
cd backend
python -m venv .venv-mllm
.\.venv-mllm\Scripts\Activate.ps1
pip install -r requirements-mllm.txt
```

Then point the FastAPI backend to that Python executable from `backend/`:

```powershell
$env:RADIOLOGY_MLLM_PYTHON=(Resolve-Path ".\.venv-mllm\Scripts\python.exe").Path
```

Generation should not be attempted until:

- `python mllm_worker\check_environment.py` exits `0`.
- `python mllm_worker\check_model_files.py` exits `0`.
- `GET /api/mllm/status` reports `worker_environment_ready: true`, `findings_mllm_ready: true`, and `impression_mllm_ready: true`.

The worker is launched as a subprocess by the backend and returns JSON to the main API process.
