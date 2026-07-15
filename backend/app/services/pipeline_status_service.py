from pathlib import Path

from app.core.config import (
    CHEXAGENT_FINDINGS_DIR,
    CHEXAGENT_IMPRESSION_DIR,
    MLLM_ALLOW_CPU,
    MOCK_OUTPUT_JSON,
    PIPELINE_MODE,
    PIPELINE_MODES_AVAILABLE,
    PLM_INFERENCE_DIR,
    RADBERT_FINDINGS_DIR,
    RADBERT_IMPRESSION_DIR,
    SOURCES_DIR,
)
from app.services.mllm_readiness_service import get_mllm_readiness
from app.services.mllm_service import get_mllm_worker_environment_status
from app.services.plm_service import get_plm_status


def _path_status(path: Path) -> dict[str, str | bool]:
    return {
        "exists": path.exists(),
        "path": str(path),
    }


def get_pipeline_readiness() -> dict:
    plm_status = get_plm_status()
    mllm_status = get_mllm_readiness()
    worker_status = get_mllm_worker_environment_status()
    checks = {
        "sources_dir": _path_status(SOURCES_DIR),
        "plm_inference_dir": _path_status(PLM_INFERENCE_DIR),
        "chexagent_findings_config": _path_status(CHEXAGENT_FINDINGS_DIR / "config.json"),
        "chexagent_impression_config": _path_status(CHEXAGENT_IMPRESSION_DIR / "config.json"),
        "radbert_findings_model": _path_status(RADBERT_FINDINGS_DIR / "model.safetensors"),
        "radbert_impression_model": _path_status(RADBERT_IMPRESSION_DIR / "model.safetensors"),
        "mock_output_json": _path_status(MOCK_OUTPUT_JSON),
    }
    mock_output_ready = checks["mock_output_json"]["exists"]
    plm_inference_modules_ready = checks["plm_inference_dir"]["exists"]
    plm_models_ready = (
        checks["radbert_findings_model"]["exists"]
        and checks["radbert_impression_model"]["exists"]
    )
    mllm_models_ready = (
        checks["chexagent_findings_config"]["exists"]
        and checks["chexagent_impression_config"]["exists"]
    )
    plm_ready = (
        plm_status["dependencies_ready"]
        and plm_status["radbert_findings_model_exists"]
        and plm_status["radbert_impression_model_exists"]
    )
    worker_cuda_available = worker_status.get("worker_cuda_available") is True
    real_pipeline_ready = (
        plm_ready
        and worker_status.get("worker_environment_ready") is True
        and mllm_status["findings_mllm_ready"]
        and mllm_status["impression_mllm_ready"]
        and (worker_cuda_available or MLLM_ALLOW_CPU)
    )
    return {
        "ready": all(item["exists"] for item in checks.values()),
        "current_pipeline_mode": PIPELINE_MODE,
        "mock_ready": mock_output_ready,
        "plm_ready": plm_ready,
        "mllm_worker_environment_ready": worker_status.get("worker_environment_ready"),
        "mllm_findings_ready": mllm_status["findings_mllm_ready"],
        "mllm_impression_ready": mllm_status["impression_mllm_ready"],
        "worker_cuda_available": worker_status.get("worker_cuda_available"),
        "effective_mllm_device": worker_status.get("effective_mllm_device"),
        "real_pipeline_ready": real_pipeline_ready,
        "mock_output_ready": mock_output_ready,
        "plm_inference_modules_ready": plm_inference_modules_ready,
        "plm_models_ready": plm_models_ready,
        "mllm_models_ready": mllm_models_ready,
        "plm_runtime_dependencies_ready": plm_status["dependencies_ready"],
        "plm_models_loaded": plm_status["models_loaded"],
        "mllm_dependencies_ready": mllm_status["dependencies_ready"],
        "findings_mllm_ready": mllm_status["findings_mllm_ready"],
        "impression_mllm_ready": mllm_status["impression_mllm_ready"],
        "findings_mllm_missing_shards": mllm_status["findings_model"]["missing_shards"],
        "impression_mllm_missing_shards": mllm_status["impression_model"]["missing_shards"],
        "cuda_available": mllm_status["cuda_available"],
        "pipeline_modes_available": PIPELINE_MODES_AVAILABLE,
        "mllm_cpu_allowed": MLLM_ALLOW_CPU,
        "checks": checks,
    }
