import json
from pathlib import Path


CUSTOM_CODE_FILES = [
    "configuration_chexagent.py",
    "modeling_chexagent.py",
    "modeling_visual.py",
    "tokenization_chexagent.py",
]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def check_model_folder(model_dir: Path) -> dict:
    index_path = model_dir / "model.safetensors.index.json"
    expected_shards = []
    index_error = None

    if index_path.exists():
        try:
            index_data = json.loads(index_path.read_text(encoding="utf-8"))
            expected_shards = sorted(set(index_data.get("weight_map", {}).values()))
        except Exception as exc:
            index_error = str(exc)

    missing_shards = [
        shard_name for shard_name in expected_shards
        if not (model_dir / shard_name).exists()
    ]
    custom_code_missing = [
        filename for filename in CUSTOM_CODE_FILES
        if not (model_dir / filename).exists()
    ]
    config_exists = (model_dir / "config.json").exists()
    tokenizer_exists = (model_dir / "tokenizer_config.json").exists()

    return {
        "model_dir": str(model_dir),
        "folder_exists": model_dir.exists(),
        "config_exists": config_exists,
        "index_exists": index_path.exists(),
        "tokenizer_exists": tokenizer_exists,
        "custom_code_missing": custom_code_missing,
        "index_error": index_error,
        "expected_shards": expected_shards,
        "missing_shards": missing_shards,
        "ready": all([
            model_dir.exists(),
            config_exists,
            index_path.exists(),
            tokenizer_exists,
            not custom_code_missing,
            index_error is None,
            bool(expected_shards),
            not missing_shards,
        ]),
    }


def print_report(name: str, status: dict) -> None:
    print(f"{name}_ready: {status['ready']}")
    print(f"{name}_model_dir: {status['model_dir']}")
    print(f"{name}_folder_exists: {status['folder_exists']}")
    print(f"{name}_config_exists: {status['config_exists']}")
    print(f"{name}_index_exists: {status['index_exists']}")
    print(f"{name}_tokenizer_exists: {status['tokenizer_exists']}")
    if status["index_error"]:
        print(f"{name}_index_error: {status['index_error']}")
    print(f"{name}_custom_code_missing: {', '.join(status['custom_code_missing'])}")
    print(f"{name}_expected_shards: {', '.join(status['expected_shards'])}")
    print(f"{name}_missing_shards: {', '.join(status['missing_shards'])}")


def main() -> int:
    root = project_root()
    findings_dir = root / "sources" / "mllm_models" / "chexagent_findings"
    impression_dir = root / "sources" / "mllm_models" / "chexagent_impression"

    findings = check_model_folder(findings_dir)
    impression = check_model_folder(impression_dir)

    print_report("findings", findings)
    print_report("impression", impression)

    return 0 if findings["ready"] and impression["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
