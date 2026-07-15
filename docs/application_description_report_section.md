# Application Description: MLLM - PLM Workflow

## 1. Purpose

`MLLM - PLM Workflow` is a research decision-support prototype for chest X-ray analysis review. It demonstrates how a multimodal large language model can generate radiology-style Findings and Impression text from an uploaded image, and how a predictive language model can convert that generated text into structured finding labels for review.

The application is intended for research, demonstration, and workflow validation. It is not a diagnostic medical device and does not replace clinical interpretation.

## 2. Workflow

The application supports the following workflow:

1. Upload a JPG, JPEG, or PNG chest X-ray image.
2. Generate Findings and Impression text with the CheXagent MLLM worker.
3. Extract 14 structured finding labels with the PLM/RadBERT stage.
4. Fuse section-level outputs into a case-level summary.
5. Present review priority, rationale, and safety messaging.
6. Export JSON, CSV, Markdown, and generated report TXT artifacts.

## 3. Backend Integration

The frontend calls the FastAPI backend endpoint:

```text
POST /api/analyze
```

The backend supports three modes through `RADIOLOGY_PIPELINE_MODE`:

- `real`: runs the full MLLM-to-PLM pipeline.
- `plm_from_precomputed_report`: runs PLM/RadBERT extraction from precomputed report text.
- `mock`: returns precomputed demo JSON.

This mode design supports real demonstrations while preserving fallback paths for environments without full model readiness.

## 4. MLLM Worker Isolation

CheXagent runs in a separate Python environment under `backend/.venv-mllm/`. The main FastAPI environment does not import CheXagent directly. Instead, the backend launches:

```text
backend/mllm_worker/generate_report_worker.py
```

through the `RADIOLOGY_MLLM_PYTHON` environment variable. This isolation avoids dependency conflicts and helps control GPU memory usage.

## 5. PLM Extraction

The PLM/RadBERT extraction stage runs in the main backend environment. It receives generated Findings and Impression text and returns structured labels with:

- final state
- confidence
- confidence level
- class probabilities
- source attribution

The 14 structured labels follow the project extraction schema and are displayed in the frontend table.

## 6. Frontend Experience

The React/Vite frontend provides:

- application header with decision-support-only framing
- image upload and preview
- analysis workflow progress
- generated Findings and Impression panels
- structured findings table
- case summary
- decision-support rationale
- export controls

The design is intentionally restrained and review-oriented. Generated report text and structured values remain selectable so users can copy outputs when needed.

## 7. Export System

Real analysis runs save latest artifacts under:

```text
backend/outputs/latest/
```

Timestamped run copies are saved under:

```text
backend/outputs/runs/
```

The export endpoints provide:

- JSON decision-support output
- CSV structured findings
- Markdown decision-support report
- TXT generated report

If latest runtime artifacts are unavailable, the backend falls back to precomputed demo artifacts.

## 8. Safety Framing

The interface and documentation consistently frame outputs as decision-support only. The generated report, structured findings, and review rationale are research artifacts that require qualified clinical review.

## 9. Current Limitations

- Real mode requires local CheXagent and PLM model files.
- Real mode is intended for a CUDA-capable environment.
- The application processes one uploaded image at a time.
- Analysis is synchronous from the frontend perspective.
- The prototype is not clinically validated for deployment.

## 10. Future Work

Potential future improvements include job-based progress updates, deployment packaging, stronger evaluation reporting, batch processing, and DICOM/PACS-oriented workflows after appropriate clinical and security review.
