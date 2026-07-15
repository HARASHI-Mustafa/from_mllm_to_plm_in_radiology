import argparse
import gc
import json
import os
import time
from pathlib import Path
from typing import Any

from check_model_files import check_model_folder, project_root


FINDINGS_PROMPT = "Structured Radiology Report Generation for Findings Section"
IMPRESSION_PROMPT = "Structured Radiology Report Generation for Impression Section"
SUPPORTED_MODES = {"findings", "impression", "report"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Isolated CheXagent report generation worker.")
    parser.add_argument("--image-path", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--mode", required=True, choices=sorted(SUPPORTED_MODES))
    return parser.parse_args()


def clean_text(text: Any) -> str:
    value = "" if text is None else str(text)
    return value.replace("<|endoftext|>", "").replace("</s>", "").strip()


def write_result(output_json: Path, result: dict[str, Any]) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2), encoding="utf-8")


def make_result(
    *,
    success: bool,
    mode: str,
    text: str,
    runtime_seconds: float,
    device: str,
    errors: list[str],
) -> dict[str, Any]:
    text_key = "impression" if mode == "impression" else "findings"
    return {
        "success": success,
        "mode": mode,
        text_key: text,
        "runtime_seconds": runtime_seconds,
        "device": device,
        "errors": errors,
    }


def make_report_result(
    *,
    success: bool,
    findings: str,
    impression: str,
    findings_seconds: float | None,
    impression_seconds: float | None,
    total_seconds: float,
    device: str,
    errors: list[str],
) -> dict[str, Any]:
    combined = ""
    if success:
        combined = f"FINDINGS:\n{findings}\n\nIMPRESSION:\n{impression}"
    return {
        "success": success,
        "mode": "report",
        "findings": findings,
        "impression": impression,
        "combined": combined,
        "runtime": {
            "findings_seconds": findings_seconds,
            "impression_seconds": impression_seconds,
            "total_seconds": total_seconds,
        },
        "device": device,
        "errors": errors,
    }


def validate_model(model_dir: Path, label: str) -> None:
    status = check_model_folder(model_dir)
    if status["ready"]:
        return

    errors = [f"CheXagent {label} model folder is not ready: {model_dir}"]
    if not status["index_exists"]:
        errors.append("Missing model.safetensors.index.json.")
    if status["index_error"]:
        errors.append(f"Invalid safetensors index JSON: {status['index_error']}")
    if status["custom_code_missing"]:
        errors.append(f"Missing custom code files: {', '.join(status['custom_code_missing'])}")
    if status["missing_shards"]:
        errors.append(f"Missing safetensors shards: {', '.join(status['missing_shards'])}")
    raise RuntimeError(" ".join(errors))


def patch_chexagent_visual_dtype(model: Any, target_dtype: Any) -> None:
    visual = getattr(getattr(model, "model", model), "visual", None)
    if visual is None:
        return
    try:
        visual.to(dtype=target_dtype)
    except Exception:
        pass


def cleanup_gpu_memory() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        pass


def gpu_memory_snapshot(label: str) -> None:
    try:
        import torch

        if not torch.cuda.is_available():
            print(f"{label}: GPU memory unavailable; CUDA is false.")
            return
        device_index = torch.cuda.current_device()
        allocated = torch.cuda.memory_allocated(device_index) // (1024 * 1024)
        reserved = torch.cuda.memory_reserved(device_index) // (1024 * 1024)
        print(f"{label}: GPU memory allocated={allocated} MiB reserved={reserved} MiB")
    except Exception as exc:
        print(f"{label}: GPU memory snapshot unavailable: {exc}")


def generate_section(
    image_path: Path,
    model_dir: Path,
    prompt: str,
    max_new_tokens: int,
) -> tuple[str, str]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    cuda_available = torch.cuda.is_available()
    device = "cuda" if cuda_available else "cpu"
    dtype = torch.float16 if cuda_available else torch.float32

    tokenizer = None
    model = None
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            str(model_dir),
            trust_remote_code=True,
            local_files_only=True,
        )

        load_kwargs: dict[str, Any] = {
            "trust_remote_code": True,
            "local_files_only": True,
            "torch_dtype": dtype,
        }
        if cuda_available:
            load_kwargs["device_map"] = {"": 0}

        model = AutoModelForCausalLM.from_pretrained(str(model_dir), **load_kwargs)
        if not cuda_available:
            model = model.to(dtype=dtype)
            model = model.to(device)

        patch_chexagent_visual_dtype(model, dtype)
        model.eval()

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
        return clean_text(tokenizer.decode(generated)), device
    finally:
        del tokenizer
        del model
        cleanup_gpu_memory()


def generate_report(image_path: Path, root: Path, device: str, start: float) -> dict[str, Any]:
    findings_dir = root / "sources" / "mllm_models" / "chexagent_findings"
    impression_dir = root / "sources" / "mllm_models" / "chexagent_impression"
    validate_model(findings_dir, "Findings")
    validate_model(impression_dir, "Impression")

    findings = ""
    impression = ""
    findings_seconds = None
    impression_seconds = None
    errors = []

    try:
        print("Starting Findings generation")
        gpu_memory_snapshot("Before Findings")
        findings_start = time.perf_counter()
        findings, device = generate_section(
            image_path=image_path,
            model_dir=findings_dir,
            prompt=FINDINGS_PROMPT,
            max_new_tokens=512,
        )
        findings_seconds = time.perf_counter() - findings_start
        print("Findings generation completed")
        gpu_memory_snapshot("After Findings")
        print("Cleaning GPU memory after Findings")
        cleanup_gpu_memory()
        gpu_memory_snapshot("After Findings cleanup")

        print("Starting Impression generation")
        gpu_memory_snapshot("Before Impression")
        impression_start = time.perf_counter()
        impression, device = generate_section(
            image_path=image_path,
            model_dir=impression_dir,
            prompt=IMPRESSION_PROMPT,
            max_new_tokens=256,
        )
        impression_seconds = time.perf_counter() - impression_start
        print("Impression generation completed")
        gpu_memory_snapshot("After Impression")
        print("Cleaning GPU memory after Impression")
        cleanup_gpu_memory()
        gpu_memory_snapshot("After Impression cleanup")
    except Exception as exc:
        errors.append(str(exc))
        return make_report_result(
            success=False,
            findings=findings,
            impression=impression,
            findings_seconds=findings_seconds,
            impression_seconds=impression_seconds,
            total_seconds=time.perf_counter() - start,
            device=device,
            errors=errors,
        )

    return make_report_result(
        success=True,
        findings=findings,
        impression=impression,
        findings_seconds=findings_seconds,
        impression_seconds=impression_seconds,
        total_seconds=time.perf_counter() - start,
        device=device,
        errors=[],
    )


def main() -> int:
    args = parse_args()
    start = time.perf_counter()
    image_path = Path(args.image_path).expanduser().resolve()
    output_json = Path(args.output_json).expanduser().resolve()
    root = project_root()
    device = "unavailable"

    os.environ.setdefault("HF_HOME", str(root / "sources" / "hf_cache"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(root / "sources" / "hf_cache" / "transformers"))
    os.environ.setdefault("HF_MODULES_CACHE", str(root / "sources" / "hf_cache" / "modules"))

    try:
        if args.mode == "findings":
            model_dir = root / "sources" / "mllm_models" / "chexagent_findings"
            label = "Findings"
            prompt = FINDINGS_PROMPT
            max_new_tokens = 512
        elif args.mode == "impression":
            model_dir = root / "sources" / "mllm_models" / "chexagent_impression"
            label = "Impression"
            prompt = IMPRESSION_PROMPT
            max_new_tokens = 256
        elif args.mode == "report":
            model_dir = None
            label = None
            prompt = None
            max_new_tokens = None
        else:
            raise NotImplementedError(f"Mode is not implemented yet: {args.mode}")

        if not image_path.exists():
            raise FileNotFoundError(f"Image path does not exist: {image_path}")

        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda":
            print(f"Using CUDA device: {torch.cuda.get_device_name(torch.cuda.current_device())}")
        else:
            print("Using CPU device.")

        if args.mode == "report":
            result = generate_report(image_path=image_path, root=root, device=device, start=start)
            write_result(output_json, result)
            return 0 if result["success"] else 1

        validate_model(model_dir, label)
        text, device = generate_section(
            image_path=image_path,
            model_dir=model_dir,
            prompt=prompt,
            max_new_tokens=max_new_tokens,
        )
        write_result(
            output_json,
            make_result(
                success=True,
                mode=args.mode,
                text=text,
                runtime_seconds=time.perf_counter() - start,
                device=device,
                errors=[],
            ),
        )
        return 0
    except Exception as exc:
        if args.mode == "report":
            write_result(
                output_json,
                make_report_result(
                    success=False,
                    findings="",
                    impression="",
                    findings_seconds=None,
                    impression_seconds=None,
                    total_seconds=time.perf_counter() - start,
                    device=device,
                    errors=[str(exc)],
                ),
            )
            print(f"Worker error: {exc}")
            return 1
        write_result(
            output_json,
            make_result(
                success=False,
                mode=args.mode,
                text="",
                runtime_seconds=time.perf_counter() - start,
                device=device,
                errors=[str(exc)],
            ),
        )
        print(f"Worker error: {exc}")
        return 1
    finally:
        cleanup_gpu_memory()


if __name__ == "__main__":
    raise SystemExit(main())
