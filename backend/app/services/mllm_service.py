import gc
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from app.core.config import (
    CHEXAGENT_FINDINGS_DIR,
    CHEXAGENT_IMPRESSION_DIR,
    HF_CACHE_DIR,
    LOCAL_FILES_ONLY,
    MLLM_ALLOW_CPU,
    PROJECT_ROOT,
)
from app.services.mllm_readiness_service import (
    check_chexagent_model_folder,
    get_mllm_dependency_status,
)


FINDINGS_PROMPT = "Structured Radiology Report Generation for Findings Section"
IMPRESSION_PROMPT = "Structured Radiology Report Generation for Impression Section"


class MLLMDependencyError(RuntimeError):
    pass


class MLLMModelFilesError(RuntimeError):
    pass


class MLLMWorkerError(RuntimeError):
    pass


def _parse_bool(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return None


def _parse_worker_environment_stdout(stdout: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "worker_cuda_available": None,
        "worker_device_name": None,
        "worker_torch_version": None,
        "worker_torch_cuda_version": None,
    }
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if line.startswith("torch:"):
            marker = "version="
            if marker in line:
                parsed["worker_torch_version"] = line.split(marker, 1)[1].strip()
        elif line.startswith("torch.version.cuda:"):
            parsed["worker_torch_cuda_version"] = line.split(":", 1)[1].strip() or None
        elif line.startswith("torch.cuda.is_available:"):
            parsed["worker_cuda_available"] = _parse_bool(line.split(":", 1)[1])
        elif line.startswith("cuda_device_name:"):
            parsed["worker_device_name"] = line.split(":", 1)[1].strip() or None
    return parsed


def get_mllm_worker_environment_status() -> dict[str, Any]:
    worker_python = os.getenv("RADIOLOGY_MLLM_PYTHON")
    script_path = PROJECT_ROOT / "backend" / "mllm_worker" / "check_environment.py"

    if not worker_python:
        return {
            "worker_environment_configured": False,
            "worker_environment_ready": False,
            "worker_python": None,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "message": "RADIOLOGY_MLLM_PYTHON is not set.",
            "worker_cuda_available": None,
            "worker_device_name": None,
            "worker_torch_version": None,
            "worker_torch_cuda_version": None,
            "effective_mllm_cuda_available": False,
            "effective_mllm_device": "cpu",
        }

    try:
        completed = subprocess.run(
            [worker_python, str(script_path)],
            cwd=str(PROJECT_ROOT / "backend"),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:
        return {
            "worker_environment_configured": True,
            "worker_environment_ready": False,
            "worker_python": worker_python,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "message": "Failed to run MLLM worker environment check.",
            "worker_cuda_available": None,
            "worker_device_name": None,
            "worker_torch_version": None,
            "worker_torch_cuda_version": None,
            "effective_mllm_cuda_available": False,
            "effective_mllm_device": "cpu",
        }

    parsed = _parse_worker_environment_stdout(completed.stdout)
    worker_cuda_available = parsed["worker_cuda_available"] is True
    return {
        "worker_environment_configured": True,
        "worker_environment_ready": completed.returncode == 0,
        "worker_python": worker_python,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "message": "MLLM worker environment check completed.",
        **parsed,
        "effective_mllm_cuda_available": worker_cuda_available,
        "effective_mllm_device": "cuda" if worker_cuda_available else "cpu",
    }


def run_mllm_generation_worker(image_path: Path, mode: str, timeout_seconds: int | None = None) -> dict[str, Any]:
    if timeout_seconds is None:
        timeout_seconds = 2400 if mode == "report" else 1200

    worker_status = get_mllm_worker_environment_status()
    if not worker_status.get("worker_environment_ready"):
        message = worker_status.get("message") or "MLLM worker environment is not ready."
        stderr = worker_status.get("stderr")
        raise MLLMWorkerError(f"{message} {stderr or ''}".strip())
    if worker_status.get("worker_cuda_available") is not True and not MLLM_ALLOW_CPU:
        raise MLLMWorkerError(
            "MLLM worker CUDA is not available. Set RADIOLOGY_MLLM_ALLOW_CPU=true to allow CPU fallback."
        )

    findings_ready = check_chexagent_model_folder(CHEXAGENT_FINDINGS_DIR)
    impression_ready = check_chexagent_model_folder(CHEXAGENT_IMPRESSION_DIR)
    if mode in {"findings", "report"} and not findings_ready["ready"]:
        raise MLLMModelFilesError(f"CheXagent Findings model folder is not ready: {CHEXAGENT_FINDINGS_DIR}")
    if mode in {"impression", "report"} and not impression_ready["ready"]:
        raise MLLMModelFilesError(f"CheXagent Impression model folder is not ready: {CHEXAGENT_IMPRESSION_DIR}")

    worker_python = os.getenv("RADIOLOGY_MLLM_PYTHON")
    if not worker_python:
        raise MLLMWorkerError("RADIOLOGY_MLLM_PYTHON is not set.")

    script_path = PROJECT_ROOT / "backend" / "mllm_worker" / "generate_report_worker.py"
    if not script_path.exists():
        raise MLLMWorkerError(f"MLLM worker script does not exist: {script_path}")

    image_path = Path(image_path).resolve()
    if not image_path.exists():
        raise MLLMWorkerError(f"Image path does not exist: {image_path}")

    output_fd, output_name = tempfile.mkstemp(
        suffix=f".{mode}.json",
        prefix="mllm_worker_",
    )
    os.close(output_fd)
    output_json = Path(output_name)
    output_json.unlink(missing_ok=True)

    cmd = [
        worker_python,
        str(script_path),
        "--image-path",
        str(image_path),
        "--output-json",
        str(output_json),
        "--mode",
        mode,
    ]

    try:
        completed = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT / "backend"),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise MLLMWorkerError(
            f"MLLM worker timed out after {timeout_seconds} seconds."
        ) from exc
    except Exception as exc:
        raise MLLMWorkerError(f"Failed to run MLLM worker: {exc}") from exc

    try:
        if output_json.exists() and output_json.stat().st_size > 0:
            result = json.loads(output_json.read_text(encoding="utf-8"))
        else:
            result = {}
    except json.JSONDecodeError as exc:
        raise MLLMWorkerError(f"MLLM worker wrote invalid JSON: {exc}") from exc
    finally:
        try:
            output_json.unlink(missing_ok=True)
        except Exception:
            pass

    result.setdefault("worker_stdout", completed.stdout)
    result.setdefault("worker_stderr", completed.stderr)
    result.setdefault("worker_returncode", completed.returncode)

    if completed.returncode != 0:
        errors = result.get("errors") or []
        details = "; ".join(str(item) for item in errors if item)
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        message_parts = ["MLLM worker failed"]
        if details:
            message_parts.append(details)
        if stderr:
            message_parts.append(f"stderr: {stderr}")
        elif stdout:
            message_parts.append(f"stdout: {stdout}")
        raise MLLMWorkerError(". ".join(message_parts))

    return result


def _ensure_dependencies() -> None:
    dependencies = get_mllm_dependency_status()
    if not dependencies["ready"]:
        raise MLLMDependencyError(
            "MLLM dependencies are not installed. Install backend/requirements-mllm.txt."
        )


def _ensure_model_ready(model_dir: Path) -> None:
    readiness = check_chexagent_model_folder(model_dir)
    if readiness["ready"]:
        return
    if readiness["missing_shards"]:
        missing = ", ".join(readiness["missing_shards"])
        raise MLLMModelFilesError(
            f"CheXagent model files are incomplete. Missing safetensors shards: {missing}"
        )
    raise MLLMModelFilesError(f"CheXagent model folder is not ready: {model_dir}")


def _configure_local_cache() -> None:
    os.environ.setdefault("HF_HOME", str(HF_CACHE_DIR))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(HF_CACHE_DIR / "transformers"))


def _get_torch_device_and_dtype():
    import torch

    if torch.cuda.is_available():
        return "cuda", torch.float16
    return "cpu", torch.float32


def gpu_memory_summary() -> dict[str, Any]:
    dependencies = get_mllm_dependency_status()
    if not dependencies["modules"]["torch"]["available"]:
        return {"available": False}

    import torch

    if not torch.cuda.is_available():
        return {"available": False, "device": "cpu"}

    device_index = torch.cuda.current_device()
    return {
        "available": True,
        "device": "cuda",
        "device_name": torch.cuda.get_device_name(device_index),
        "allocated_bytes": int(torch.cuda.memory_allocated(device_index)),
        "reserved_bytes": int(torch.cuda.memory_reserved(device_index)),
    }


def strong_cleanup() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        pass


def clean_text(text: Any) -> str:
    value = "" if text is None else str(text)
    return value.replace("<|endoftext|>", "").replace("</s>", "").strip()


def patch_chexagent_visual_dtype(model: Any, target_dtype: Any) -> None:
    visual = getattr(getattr(model, "model", model), "visual", None)
    if visual is None:
        return
    try:
        visual.to(dtype=target_dtype)
    except Exception:
        pass


def load_chexagent_model(model_dir: Path):
    _ensure_dependencies()
    _ensure_model_ready(model_dir)
    _configure_local_cache()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device, dtype = _get_torch_device_and_dtype()
    tokenizer = AutoTokenizer.from_pretrained(
        str(model_dir),
        trust_remote_code=True,
        local_files_only=LOCAL_FILES_ONLY,
    )

    load_kwargs = {
        "trust_remote_code": True,
        "local_files_only": LOCAL_FILES_ONLY,
        "torch_dtype": dtype,
    }
    if device == "cuda":
        load_kwargs["device_map"] = {"": 0}

    model = AutoModelForCausalLM.from_pretrained(str(model_dir), **load_kwargs)
    if device == "cpu":
        model = model.to(dtype=dtype)
        model = model.to(device)

    patch_chexagent_visual_dtype(model, dtype)
    model.eval()
    return tokenizer, model, device


def generate_section_with_chexagent(
    tokenizer: Any,
    model: Any,
    image_path: Path,
    prompt: str,
    max_new_tokens: int,
) -> str:
    import torch

    query = tokenizer.from_list_format([
        {"image": str(image_path)},
        {"text": prompt},
    ])
    conversation = [
        {"from": "system", "value": "You are a helpful assistant."},
        {"from": "human", "value": query},
    ]
    input_ids = tokenizer.apply_chat_template(
        conversation,
        add_generation_prompt=True,
        return_tensors="pt",
    )

    model_device = next(model.parameters()).device
    with torch.no_grad():
        output = model.generate(
            input_ids.to(model_device),
            do_sample=False,
            num_beams=1,
            temperature=1.0,
            top_p=1.0,
            use_cache=True,
            max_new_tokens=max_new_tokens,
        )[0]

    generated = output[input_ids.size(1):]
    if len(generated) > 0:
        generated = generated[:-1]
    return clean_text(tokenizer.decode(generated))


def _generate_section(
    image_path: Path,
    model_dir: Path,
    section: str,
    prompt: str,
    max_new_tokens: int,
    unload_after: bool,
) -> dict[str, Any]:
    start = time.perf_counter()
    tokenizer = None
    model = None
    device = "unavailable"

    try:
        tokenizer, model, device = load_chexagent_model(model_dir)
        text = generate_section_with_chexagent(
            tokenizer=tokenizer,
            model=model,
            image_path=image_path,
            prompt=prompt,
            max_new_tokens=max_new_tokens,
        )
        return {
            "section": section,
            "text": text,
            "runtime_seconds": time.perf_counter() - start,
            "model_dir": str(model_dir),
            "device": device,
            "success": True,
            "error": None,
        }
    finally:
        if unload_after:
            del tokenizer
            del model
            strong_cleanup()


def generate_findings_from_image(image_path: Path, unload_after: bool = True) -> dict[str, Any]:
    return _generate_section(
        image_path=image_path,
        model_dir=CHEXAGENT_FINDINGS_DIR,
        section="findings",
        prompt=FINDINGS_PROMPT,
        max_new_tokens=512,
        unload_after=unload_after,
    )


def generate_impression_from_image(image_path: Path, unload_after: bool = True) -> dict[str, Any]:
    return _generate_section(
        image_path=image_path,
        model_dir=CHEXAGENT_IMPRESSION_DIR,
        section="impression",
        prompt=IMPRESSION_PROMPT,
        max_new_tokens=256,
        unload_after=unload_after,
    )


def generate_report_from_image(image_path: Path) -> dict[str, Any]:
    start = time.perf_counter()
    errors = []

    findings_result = generate_findings_from_image(image_path, unload_after=True)
    if not findings_result["success"]:
        errors.append(findings_result.get("error"))

    impression_result = generate_impression_from_image(image_path, unload_after=True)
    if not impression_result["success"]:
        errors.append(impression_result.get("error"))

    findings_text = findings_result.get("text", "")
    impression_text = impression_result.get("text", "")

    return {
        "findings": findings_text,
        "impression": impression_text,
        "combined": f"FINDINGS:\n{findings_text}\n\nIMPRESSION:\n{impression_text}",
        "runtime": {
            "findings_seconds": findings_result.get("runtime_seconds"),
            "impression_seconds": impression_result.get("runtime_seconds"),
            "total_seconds": time.perf_counter() - start,
        },
        "success": len(errors) == 0,
        "errors": errors,
    }
