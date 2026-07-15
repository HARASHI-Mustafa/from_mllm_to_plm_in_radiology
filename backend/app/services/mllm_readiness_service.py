import importlib.metadata
import importlib.util
import json
from pathlib import Path
from typing import Any

from app.core.config import (
    CHEXAGENT_FINDINGS_DIR,
    CHEXAGENT_IMPRESSION_DIR,
    MLLM_EXTERNAL_SHARDS_DIR,
)


CUSTOM_CODE_FILES = [
    "configuration_chexagent.py",
    "modeling_chexagent.py",
    "modeling_visual.py",
    "tokenization_chexagent.py",
]

REQUIRED_MODEL_FILES = [
    "config.json",
    "model.safetensors.index.json",
    "tokenizer_config.json",
]

DEPENDENCY_MODULES = {
    "torch": "torch",
    "transformers": "transformers",
    "PIL": "Pillow",
    "safetensors": "safetensors",
    "accelerate": "accelerate",
    "einops": "einops",
}


def _dependency_status(module_name: str, package_name: str) -> dict[str, Any]:
    available = importlib.util.find_spec(module_name) is not None
    version = None
    if available:
        try:
            version = importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            version = None
    return {
        "available": available,
        "version": version,
    }


def get_mllm_dependency_status() -> dict[str, Any]:
    modules = {
        module_name: _dependency_status(module_name, package_name)
        for module_name, package_name in DEPENDENCY_MODULES.items()
    }
    cuda_available = None
    device = "unavailable"
    if modules["torch"]["available"]:
        try:
            import torch

            cuda_available = torch.cuda.is_available()
            device = "cuda" if cuda_available else "cpu"
        except Exception:
            cuda_available = None
            device = "unavailable"

    return {
        "ready": all(item["available"] for item in modules.values()),
        "modules": modules,
        "cuda_available": cuda_available,
        "device": device,
    }


def _safe_read_expected_shards(index_path: Path) -> tuple[list[str], str | None]:
    if not index_path.exists():
        return [], None
    try:
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], f"Invalid safetensors index JSON: {exc}"

    weight_map = index_data.get("weight_map")
    if not isinstance(weight_map, dict):
        return [], "Safetensors index is missing weight_map."

    return sorted(set(str(filename) for filename in weight_map.values())), None


def check_chexagent_model_folder(model_dir: Path) -> dict[str, Any]:
    model_dir = Path(model_dir)
    index_path = model_dir / "model.safetensors.index.json"
    expected_shards, index_error = _safe_read_expected_shards(index_path)
    missing_shards = [
        shard_name for shard_name in expected_shards
        if not (model_dir / shard_name).exists()
    ]
    custom_code_missing = [
        filename for filename in CUSTOM_CODE_FILES
        if not (model_dir / filename).exists()
    ]

    folder_exists = model_dir.exists()
    config_exists = (model_dir / "config.json").exists()
    index_exists = index_path.exists()
    tokenizer_exists = (model_dir / "tokenizer_config.json").exists()
    custom_code_ready = len(custom_code_missing) == 0
    all_shards_ready = bool(expected_shards) and len(missing_shards) == 0 and index_error is None

    return {
        "model_dir": str(model_dir),
        "folder_exists": folder_exists,
        "config_exists": config_exists,
        "index_exists": index_exists,
        "tokenizer_exists": tokenizer_exists,
        "custom_code_ready": custom_code_ready,
        "custom_code_missing": custom_code_missing,
        "index_error": index_error,
        "expected_shards": expected_shards,
        "missing_shards": missing_shards,
        "all_shards_ready": all_shards_ready,
        "ready": all([
            folder_exists,
            config_exists,
            index_exists,
            tokenizer_exists,
            custom_code_ready,
            all_shards_ready,
        ]),
    }


def _external_shards_summary() -> dict[str, Any]:
    shard_files = []
    if MLLM_EXTERNAL_SHARDS_DIR.exists():
        shard_files = sorted(path.name for path in MLLM_EXTERNAL_SHARDS_DIR.glob("*.safetensors"))
    return {
        "path": str(MLLM_EXTERNAL_SHARDS_DIR),
        "exists": MLLM_EXTERNAL_SHARDS_DIR.exists(),
        "safetensors_count": len(shard_files),
        "safetensors_files": shard_files,
    }


def get_mllm_readiness() -> dict[str, Any]:
    dependencies = get_mllm_dependency_status()
    findings = check_chexagent_model_folder(CHEXAGENT_FINDINGS_DIR)
    impression = check_chexagent_model_folder(CHEXAGENT_IMPRESSION_DIR)

    return {
        "dependencies_ready": dependencies["ready"],
        "dependencies": dependencies["modules"],
        "cuda_available": dependencies["cuda_available"],
        "device": dependencies["device"],
        "findings_model": findings,
        "impression_model": impression,
        "findings_mllm_ready": findings["ready"],
        "impression_mllm_ready": impression["ready"],
        "external_shards": _external_shards_summary(),
        "ready": dependencies["ready"] and findings["ready"] and impression["ready"],
    }
