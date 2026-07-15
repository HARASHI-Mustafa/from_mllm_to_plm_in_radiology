from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import PIPELINE_MODE
from app.schemas.analysis_schema import PLMTextRequest
from app.services.export_service import (
    get_generated_report_txt_path,
    get_markdown_report_path,
    get_mock_json_path,
    get_structured_csv_path,
)
from app.services.file_service import save_uploaded_image
from app.services.mock_result_service import load_mock_analysis_result
from app.services.mllm_readiness_service import get_mllm_readiness
from app.services.mllm_service import (
    MLLMDependencyError,
    MLLMModelFilesError,
    MLLMWorkerError,
    get_mllm_worker_environment_status,
    run_mllm_generation_worker,
)
from app.services.pipeline_status_service import get_pipeline_readiness
from app.services.plm_service import (
    PLMDependencyError,
    PLMModelFilesError,
    get_plm_status,
    get_precomputed_report_sections,
    run_plm_extraction,
)
from app.services.real_pipeline_service import run_real_pipeline

router = APIRouter(prefix="/api")


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/pipeline/status")
def pipeline_status() -> dict:
    return get_pipeline_readiness()


@router.get("/mllm/status")
def mllm_status() -> dict:
    status = get_mllm_readiness()
    worker_status = get_mllm_worker_environment_status()
    main_process_cuda_available = status.pop("cuda_available", None)
    main_process_device = status.pop("device", "unavailable")
    status["main_process_cuda_available"] = main_process_cuda_available
    status["main_process_device"] = main_process_device
    status.update(worker_status)
    status["recommendation"] = (
        "Use a separate MLLM environment to avoid dependency conflicts with PLM."
    )
    return status


def _handle_mllm_generation_error(exc: Exception) -> None:
    if isinstance(exc, MLLMDependencyError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, MLLMModelFilesError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, MLLMWorkerError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail=f"MLLM generation failed: {exc}") from exc


@router.post("/mllm/generate/findings")
async def generate_mllm_findings(file: UploadFile = File(...)) -> dict:
    saved_image_path = await save_uploaded_image(file)
    try:
        return run_mllm_generation_worker(saved_image_path, mode="findings")
    except Exception as exc:
        _handle_mllm_generation_error(exc)


@router.post("/mllm/generate/impression")
async def generate_mllm_impression(file: UploadFile = File(...)) -> dict:
    saved_image_path = await save_uploaded_image(file)
    try:
        return run_mllm_generation_worker(saved_image_path, mode="impression")
    except Exception as exc:
        _handle_mllm_generation_error(exc)


@router.post("/mllm/generate/report")
async def generate_mllm_report(file: UploadFile = File(...)) -> dict:
    saved_image_path = await save_uploaded_image(file)
    try:
        return run_mllm_generation_worker(saved_image_path, mode="report")
    except Exception as exc:
        _handle_mllm_generation_error(exc)


@router.get("/plm/status")
def plm_status() -> dict:
    return get_plm_status()


@router.post("/plm/extract")
def plm_extract(request: PLMTextRequest) -> dict:
    try:
        return run_plm_extraction(request.findings, request.impression)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PLMDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PLMModelFilesError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/analyze")
async def analyze_image(file: UploadFile = File(...)) -> dict:
    saved_image_path = await save_uploaded_image(file)

    if PIPELINE_MODE == "mock":
        result = load_mock_analysis_result()
        result["api_metadata"] = {
            "mode": "mock_outputs",
            "uploaded_image_saved": str(saved_image_path),
            "note": "Returned precomputed pipeline output while real integration is being prepared.",
        }
        return result

    if PIPELINE_MODE == "plm_from_precomputed_report":
        try:
            findings, impression = get_precomputed_report_sections()
            result = run_plm_extraction(findings, impression)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except PLMDependencyError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except PLMModelFilesError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        result["api_metadata"] = {
            "mode": "plm_from_precomputed_report",
            "uploaded_image_saved": str(saved_image_path),
            "note": "Used precomputed Findings and Impression text, then ran PLM structured extraction.",
        }
        return result

    if PIPELINE_MODE != "real":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported RADIOLOGY_PIPELINE_MODE: {PIPELINE_MODE}",
        )

    try:
        return run_real_pipeline(saved_image_path)
    except MLLMWorkerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except MLLMModelFilesError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PLMDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PLMModelFilesError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/exports/json")
def export_json() -> FileResponse:
    return FileResponse(
        get_mock_json_path(),
        media_type="application/json",
        filename="decision_support_output.json",
    )


@router.get("/exports/csv")
def export_csv() -> FileResponse:
    return FileResponse(
        get_structured_csv_path(),
        media_type="text/csv",
        filename="structured_findings.csv",
    )


@router.get("/exports/markdown")
def export_markdown() -> FileResponse:
    return FileResponse(
        get_markdown_report_path(),
        media_type="text/markdown",
        filename="decision_support_report.md",
    )


@router.get("/exports/generated-report")
def export_generated_report() -> FileResponse:
    return FileResponse(
        get_generated_report_txt_path(),
        media_type="text/plain",
        filename="generated_report.txt",
    )
