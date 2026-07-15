import time
from pathlib import Path
from typing import Any

from app.services.export_service import save_real_run_artifacts
from app.services.mllm_service import MLLMWorkerError, run_mllm_generation_worker
from app.services.plm_service import run_plm_extraction


def _require_text(value: Any, label: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise MLLMWorkerError(f"MLLM worker returned empty {label}.")
    return text


def run_real_pipeline(image_path: Path) -> dict[str, Any]:
    pipeline_start = time.perf_counter()
    mllm_result = run_mllm_generation_worker(image_path, mode="report")

    findings = _require_text(mllm_result.get("findings"), "findings")
    impression = _require_text(mllm_result.get("impression"), "impression")
    combined = mllm_result.get("combined") or f"FINDINGS:\n{findings}\n\nIMPRESSION:\n{impression}"
    mllm_runtime = mllm_result.get("runtime") or {}

    plm_start = time.perf_counter()
    result = run_plm_extraction(findings, impression)
    plm_runtime_seconds = time.perf_counter() - plm_start

    result["generated_report"] = {
        "findings": findings,
        "impression": impression,
        "combined": combined,
    }
    result["api_metadata"] = {
        "mode": "real",
        "uploaded_image_saved": str(image_path),
        "mllm_worker_used": True,
        "mllm_device": mllm_result.get("device"),
        "mllm_runtime": mllm_runtime,
        "plm_used": True,
        "plm_runtime_seconds": plm_runtime_seconds,
        "total_pipeline_runtime_seconds": time.perf_counter() - pipeline_start,
        "note": "Generated Findings and Impression with CheXagent worker, then extracted structured findings with PLM/RadBERT.",
    }

    artifact_paths = save_real_run_artifacts(result)
    result["api_metadata"]["artifacts_saved"] = True
    result["api_metadata"]["artifact_paths"] = artifact_paths
    return result
