import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

from app.core.config import (
    HF_CACHE_DIR,
    MOCK_OUTPUT_JSON,
    RADBERT_FINDINGS_DIR,
    RADBERT_IMPRESSION_DIR,
    SOURCES_DIR,
)


class PLMDependencyError(RuntimeError):
    pass


class PLMModelFilesError(RuntimeError):
    pass


_PIPELINE = None
_DEVICE = None

HIGH_RISK_LABELS = {
    "Enlarged Cardiomediastinum",
    "Lung Lesion",
    "Consolidation",
    "Pneumonia",
    "Pneumothorax",
    "Fracture",
}

RELATIVELY_RELIABLE_LABELS = {
    "Lung Opacity",
    "Pleural Effusion",
    "Support Devices",
}

LOW_SUPPORT_LABELS = {
    "No Finding",
    "Pleural Other",
}


def _dependency_status() -> dict[str, Any]:
    required = ["torch", "transformers", "safetensors", "numpy", "pandas", "sklearn"]
    modules = {name: importlib.util.find_spec(name) is not None for name in required}
    return {
        "ready": all(modules.values()),
        "modules": modules,
    }


def _ensure_dependencies() -> None:
    if not _dependency_status()["ready"]:
        raise PLMDependencyError(
            "PLM inference dependencies are not installed. Install backend/requirements-inference.txt."
        )


def _ensure_model_files() -> None:
    if not (RADBERT_FINDINGS_DIR / "model.safetensors").exists():
        raise PLMModelFilesError("PLM model files were not found in sources/plm_models/.")
    if not (RADBERT_IMPRESSION_DIR / "model.safetensors").exists():
        raise PLMModelFilesError("PLM model files were not found in sources/plm_models/.")


def _prepare_import_path() -> None:
    sources_path = str(SOURCES_DIR)
    if sources_path not in sys.path:
        sys.path.insert(0, sources_path)


def _configure_hf_cache() -> None:
    os.environ.setdefault("HF_HOME", str(HF_CACHE_DIR))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(HF_CACHE_DIR / "transformers"))


def plm_models_loaded() -> bool:
    return _PIPELINE is not None


def get_plm_status() -> dict[str, Any]:
    dependency_status = _dependency_status()
    device = "unavailable"
    if dependency_status["modules"].get("torch"):
        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "unavailable"

    return {
        "dependencies_ready": dependency_status["ready"],
        "dependencies": dependency_status["modules"],
        "plm_inference_exists": (SOURCES_DIR / "plm_inference").exists(),
        "radbert_findings_model_exists": (RADBERT_FINDINGS_DIR / "model.safetensors").exists(),
        "radbert_impression_model_exists": (RADBERT_IMPRESSION_DIR / "model.safetensors").exists(),
        "models_loaded": plm_models_loaded(),
        "device": device,
    }


def _get_pipeline():
    global _PIPELINE, _DEVICE

    if _PIPELINE is not None:
        return _PIPELINE

    _ensure_dependencies()
    _ensure_model_files()
    _prepare_import_path()
    _configure_hf_cache()

    import torch
    from plm_inference.pipeline import SectionAwarePLMPipeline

    _DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    pipeline = SectionAwarePLMPipeline(
        impression_model_dir=RADBERT_IMPRESSION_DIR,
        findings_model_dir=RADBERT_FINDINGS_DIR,
        device=_DEVICE,
    )
    pipeline.load_models()
    _PIPELINE = pipeline
    return _PIPELINE


def _confidence_level(confidence: float | None) -> str:
    if confidence is None:
        return "low"
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.70:
        return "medium"
    return "low"


def _label_reliability(label: str) -> str:
    if label in HIGH_RISK_LABELS:
        return "high_risk_label"
    if label in LOW_SUPPORT_LABELS:
        return "low_support_interpret_with_caution"
    if label in RELATIVELY_RELIABLE_LABELS:
        return "relatively_reliable"
    return "moderate_reliability"


def _section_probabilities(section_output: dict | None, label: str) -> dict[str, float]:
    default = {
        "not_mentioned": 1.0,
        "absent": 0.0,
        "uncertain": 0.0,
        "present": 0.0,
    }
    if section_output is None:
        return default
    return section_output.get(label, {}).get("class_probabilities", default)


def _adapt_pipeline_output(plm_output: dict[str, Any], findings_text: str, impression_text: str) -> dict[str, Any]:
    from plm_inference.labels import ABNORMAL_LABELS, LABEL_COLUMNS

    fused = plm_output["fused_findings"]
    findings_output = plm_output.get("findings_output")
    impression_output = plm_output.get("impression_output")

    structured_findings = {}
    low_confidence_labels = []

    for label in LABEL_COLUMNS:
        item = fused[label]
        source = item.get("source", "impression+findings")
        if source == "findings":
            section_output = findings_output
            frontend_source = "generated_findings"
        elif source == "impression":
            section_output = impression_output
            frontend_source = "generated_impression"
        else:
            findings_probability = item.get("findings_probability") or 0.0
            impression_probability = item.get("impression_probability") or 0.0
            if findings_probability >= impression_probability:
                section_output = findings_output
                frontend_source = "generated_findings"
            else:
                section_output = impression_output
                frontend_source = "generated_impression"

        probabilities = _section_probabilities(section_output, label)
        final_state = item["final_state"]
        confidence = float(probabilities.get(final_state, item.get("findings_probability") or item.get("impression_probability") or 0.0))
        confidence_level = _confidence_level(confidence)
        if confidence < 0.70:
            low_confidence_labels.append(label)

        structured_findings[label] = {
            "state": final_state,
            "confidence": confidence,
            "confidence_level": confidence_level,
            "source": frontend_source,
            "probabilities": probabilities,
            "label_reliability_from_200_case_safety_analysis": _label_reliability(label),
        }

    present_abnormal = [
        label for label in ABNORMAL_LABELS
        if structured_findings[label]["state"] == "present"
    ]
    uncertain_abnormal = [
        label for label in ABNORMAL_LABELS
        if structured_findings[label]["state"] in {"uncertain", "conflict"}
    ]
    active_abnormal = uncertain_abnormal + present_abnormal
    high_risk_active = [
        label for label in active_abnormal
        if _label_reliability(label) in {"high_risk_label", "low_support_interpret_with_caution"}
    ]

    no_finding_state = structured_findings["No Finding"]["state"]
    no_finding_contradiction = no_finding_state == "present" and len(active_abnormal) > 0
    review_recommended = bool(active_abnormal or low_confidence_labels or high_risk_active)

    reasons = []
    if present_abnormal:
        reasons.append("One or more abnormal findings are extracted as present.")
    if uncertain_abnormal:
        reasons.append("One or more abnormal findings are extracted as uncertain.")
    if low_confidence_labels:
        reasons.append("One or more PLM labels have low confidence.")
    if high_risk_active:
        reasons.append("One or more active findings belong to high-risk or low-support labels from the 200-case safety analysis.")

    if high_risk_active:
        review_priority = "high"
    elif review_recommended:
        review_priority = "medium"
    else:
        review_priority = "low"

    return {
        "generated_report": {
            "findings": findings_text,
            "impression": impression_text,
            "combined": f"FINDINGS:\n{findings_text}\n\nIMPRESSION:\n{impression_text}",
        },
        "structured_findings": structured_findings,
        "case_summary": {
            "case_status": "abnormal_findings_detected" if active_abnormal else "no_major_report_finding_detected",
            "present_abnormal_findings": present_abnormal,
            "uncertain_abnormal_findings": uncertain_abnormal,
            "active_abnormal_findings": active_abnormal,
            "no_finding_state": no_finding_state,
        },
        "consistency_and_safety_checks": {
            "no_finding_contradiction": no_finding_contradiction,
            "no_finding_consistency_passed": not no_finding_contradiction,
            "low_confidence_threshold": 0.7,
            "low_confidence_labels": low_confidence_labels,
            "high_risk_active_labels": high_risk_active,
        },
        "decision_support": {
            "review_recommended": review_recommended,
            "review_priority": review_priority,
            "reasons": reasons,
            "final_note": "This is a decision-support output. It is not a final diagnosis.",
        },
        "plm_internal_metadata": plm_output.get("metadata", {}),
    }


def run_plm_extraction(findings_text: str, impression_text: str) -> dict[str, Any]:
    if not findings_text or not findings_text.strip() or not impression_text or not impression_text.strip():
        raise ValueError("Findings and impression text are required for PLM extraction.")

    pipeline = _get_pipeline()
    result = pipeline.run_single_report_inference(
        findings_text=findings_text,
        impression_text=impression_text,
        metadata={"source": "fastapi_plm_extract"},
    )
    return _adapt_pipeline_output(result, findings_text.strip(), impression_text.strip())


def get_precomputed_report_sections() -> tuple[str, str]:
    import json

    with MOCK_OUTPUT_JSON.open("r", encoding="utf-8") as result_file:
        result = json.load(result_file)

    generated_report = result.get("generated_report") or {}
    findings = generated_report.get("findings")
    impression = generated_report.get("impression")
    if not findings or not impression:
        raise ValueError("Findings and impression text are required for PLM extraction.")
    return findings, impression
