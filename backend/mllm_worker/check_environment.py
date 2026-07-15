import importlib
import importlib.metadata
import sys


REQUIRED_IMPORTS = {
    "torch": "torch",
    "transformers": "transformers",
    "PIL": "Pillow",
    "accelerate": "accelerate",
    "einops": "einops",
    "safetensors": "safetensors",
    "numpy": "numpy",
}


def _version(package_name: str) -> str:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def main() -> int:
    print(f"python_executable: {sys.executable}")
    print(f"python_version: {sys.version}")

    missing = []
    imported = {}

    for module_name, package_name in REQUIRED_IMPORTS.items():
        try:
            importlib.import_module(module_name)
            imported[module_name] = True
            print(f"{module_name}: ok version={_version(package_name)}")
        except Exception as exc:
            imported[module_name] = False
            missing.append(module_name)
            print(f"{module_name}: missing error={exc}")

    if imported.get("torch"):
        import torch

        cuda_available = torch.cuda.is_available()
        print(f"torch.version.cuda: {torch.version.cuda}")
        print(f"torch.cuda.is_available: {cuda_available}")
        if cuda_available:
            print(f"cuda_device_name: {torch.cuda.get_device_name(torch.cuda.current_device())}")

    if missing:
        print(f"missing_imports: {', '.join(missing)}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
