.\.venv\Scripts\Activate.ps1

$env:RADIOLOGY_PIPELINE_MODE="real"

$env:RADIOLOGY_MLLM_PYTHON="$PSScriptRoot\.venv-mllm\Scripts\python.exe"

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000