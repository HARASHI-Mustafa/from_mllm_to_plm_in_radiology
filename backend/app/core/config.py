import os
from pathlib import Path


def _get_project_root() -> Path:
    configured_root = os.getenv("RADIOLOGY_PROJECT_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


PROJECT_ROOT = _get_project_root()
USE_MOCK_OUTPUTS = _env_flag("RADIOLOGY_USE_MOCK_OUTPUTS", True)

SOURCES_DIR = PROJECT_ROOT / "sources"
INPUT_IMAGES_DIR = SOURCES_DIR / "input_images"
OUTPUTS_DIR = SOURCES_DIR / "outputs"
FINAL_DEMO_OUTPUTS_DIR = OUTPUTS_DIR / "final_whole_system_demo"
MOCK_OUTPUT_JSON = (
    FINAL_DEMO_OUTPUTS_DIR / "decision_support_output_example_cxr_20260709_110714.json"
)
MOCK_STRUCTURED_CSV = (
    FINAL_DEMO_OUTPUTS_DIR / "structured_findings_example_cxr_20260709_110714.csv"
)
MOCK_REPORT_MD = (
    FINAL_DEMO_OUTPUTS_DIR / "decision_support_report_example_cxr_20260709_110714.md"
)
MOCK_GENERATED_REPORT_TXT = (
    FINAL_DEMO_OUTPUTS_DIR / "generated_report_example_cxr_20260709_110714.txt"
)

MLLM_MODELS_DIR = SOURCES_DIR / "mllm_models"
CHEXAGENT_FINDINGS_DIR = MLLM_MODELS_DIR / "chexagent_findings"
CHEXAGENT_IMPRESSION_DIR = MLLM_MODELS_DIR / "chexagent_impression"
MLLM_EXTERNAL_SHARDS_DIR = SOURCES_DIR / "models"
PLM_MODELS_DIR = SOURCES_DIR / "plm_models"
RADBERT_FINDINGS_DIR = PLM_MODELS_DIR / "radbert_findings_model"
RADBERT_IMPRESSION_DIR = PLM_MODELS_DIR / "radbert_impression_model"
PLM_INFERENCE_DIR = SOURCES_DIR / "plm_inference"
HF_CACHE_DIR = SOURCES_DIR / "hf_cache"
LOCAL_FILES_ONLY = _env_flag("RADIOLOGY_LOCAL_FILES_ONLY", True)
MLLM_ALLOW_CPU = _env_flag("RADIOLOGY_MLLM_ALLOW_CPU", False)
UPLOADS_DIR = PROJECT_ROOT / "backend" / "uploads"
BACKEND_OUTPUTS_DIR = PROJECT_ROOT / "backend" / "outputs"
LATEST_OUTPUTS_DIR = BACKEND_OUTPUTS_DIR / "latest"
RUN_OUTPUTS_DIR = BACKEND_OUTPUTS_DIR / "runs"
PIPELINE_MODE = os.getenv(
    "RADIOLOGY_PIPELINE_MODE",
    "mock" if USE_MOCK_OUTPUTS else "real",
).strip().lower()
PIPELINE_MODES_AVAILABLE = ["mock", "plm_from_precomputed_report", "real"]

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
LATEST_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
RUN_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
