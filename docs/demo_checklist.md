# Demo Checklist

## Before Demo

- Start the backend in real mode.
- Set `RADIOLOGY_MLLM_PYTHON` to the separate MLLM worker Python executable.
- Check `GET /api/pipeline/status`.
- Confirm:
  - `current_pipeline_mode: real`
  - `real_pipeline_ready: true`
  - `worker_cuda_available: true`
  - `effective_mllm_device: cuda`
  - `plm_ready: true`
- Start the frontend with `npm run dev`.
- Check GPU availability with `nvidia-smi`.
- Close unnecessary GPU-heavy applications.
- Prepare `sources/input_images/example_cxr.jpg`.
- Run `/api/analyze` once before the presentation if time allows.
- Confirm export endpoints return files:
  - `/api/exports/json`
  - `/api/exports/csv`
  - `/api/exports/markdown`
  - `/api/exports/generated-report`

## Start Commands

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:RADIOLOGY_PIPELINE_MODE="real"
$env:RADIOLOGY_MLLM_PYTHON=(Resolve-Path ".\.venv-mllm\Scripts\python.exe").Path
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev
```

## During Demo

- Open `MLLM - PLM Workflow` in the browser.
- Upload `sources/input_images/example_cxr.jpg`.
- Run analysis.
- Explain that CheXagent generates Findings and Impression in a separate CUDA worker process.
- Explain that PLM/RadBERT extracts structured findings from the generated report text.
- Show the generated Findings and Impression.
- Show the 14-label structured findings table.
- Explain the decision-support summary and review priority.
- Show export buttons for JSON, CSV, Markdown, and generated report TXT.
- Mention clearly: this is decision-support only and not a final diagnosis.

## Fallback Plan

If real mode fails:

1. Switch to `RADIOLOGY_PIPELINE_MODE=plm_from_precomputed_report` to demonstrate real PLM extraction from precomputed report text.
2. If needed, switch to `RADIOLOGY_PIPELINE_MODE=mock` to demonstrate the full frontend experience from precomputed JSON.
3. Explain that the fallback modes are included to make the demo robust without changing the UI.

## Recommended Screenshots

- Empty dashboard.
- Image uploaded with CXR preview.
- Loading state during analysis.
- Full real analysis result.
- Generated Findings and Impression.
- Structured findings table.
- Decision-support summary.
- Export panel.
