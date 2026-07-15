# Final Application Summary

## Application Objective

`MLLM - PLM Workflow` is a research prototype that demonstrates a full chest X-ray decision-support workflow. It generates a radiology-style report from an image, extracts structured findings from the generated text, and presents the result in a review dashboard.

The goal is to connect multimodal large language model report generation with specialized predictive language model extraction for structured and reviewable radiology decision support.

## Architecture

The application has three main layers:

- React/Vite frontend for image upload, workflow display, result review, and exports.
- FastAPI backend for API routing, pipeline orchestration, PLM inference, artifact saving, and export endpoints.
- Local `sources/` resources for model files, inference modules, sample images, and precomputed fallback outputs.

## Backend FastAPI

The backend exposes health, readiness, PLM, MLLM, analysis, and export endpoints. The central endpoint is:

```text
POST /api/analyze
```

Depending on `RADIOLOGY_PIPELINE_MODE`, this endpoint can return mock output, run PLM extraction from a precomputed report, or run the complete real MLLM-to-PLM pipeline.

## MLLM Worker Separation

CheXagent runs in a separate Python environment under `backend/.venv-mllm/`. The main backend never imports CheXagent or its pinned Transformers runtime. Instead, FastAPI launches:

```text
backend/mllm_worker/generate_report_worker.py
```

as a subprocess through `RADIOLOGY_MLLM_PYTHON`.

In real report mode, the worker:

1. Loads the CheXagent Findings model.
2. Generates Findings from the CXR image.
3. Cleans GPU memory.
4. Loads the CheXagent Impression model.
5. Generates Impression from the same image.
6. Cleans GPU memory again.
7. Returns JSON to the backend.

This separation avoids dependency conflicts with the PLM/RadBERT environment and reduces GPU memory pressure by not loading both CheXagent models simultaneously.

## PLM Extraction

The PLM/RadBERT stage runs in the main backend environment. It takes generated Findings and Impression text and extracts 14 structured finding labels with states, confidence scores, confidence levels, source attribution, and class probabilities.

The frontend-compatible output includes:

- `generated_report`
- `structured_findings`
- `case_summary`
- `consistency_and_safety_checks`
- `decision_support`
- `api_metadata`

## React Frontend

The frontend is a decision-support review dashboard built with React and Vite. It includes:

- Header with status badges.
- CXR upload workspace and preview.
- Analysis workflow control.
- Case summary.
- Generated Findings and Impression.
- Structured findings table.
- Decision-support summary.
- Export panel.

The UI is designed for a research/demo setting and emphasizes clinical clarity, restrained colors, readable report text, and transparent decision-support framing.

## Export System

Real `/api/analyze` runs save latest artifacts under:

```text
backend/outputs/latest/
```

and timestamped copies under:

```text
backend/outputs/runs/
```

Available exports:

- JSON decision-support output.
- CSV structured findings table.
- Markdown decision-support report.
- TXT generated report.

Export endpoints fall back to precomputed demo artifacts if no latest real run is available.

## Safety Disclaimer

This application is a research decision-support prototype. It is not a diagnostic medical device and does not replace clinical review. Outputs must be reviewed by qualified clinical professionals before any clinical use.

## Current Limitations

- The real MLLM pipeline requires local CheXagent model files and a working CUDA-capable worker environment for practical runtime.
- The application currently processes one uploaded image at a time.
- Backend execution is synchronous from the frontend perspective; there is no streaming progress channel.
- The PLM output depends on generated report text quality.
- The frontend is optimized for demo and review, not hospital deployment or DICOM/PACS integration.

## Future Improvements

- Add streaming or job-based progress updates for long-running real pipeline calls.
- Add authentication and deployment hardening.
- Add stronger audit logging for research evaluation.
- Add batch processing and queue support.
- Add more systematic validation against curated radiology datasets.
- Add optional DICOM ingestion or integration with a viewer workflow.
- Add calibration and uncertainty reporting improvements for clinical review workflows.
