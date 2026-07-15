# Sources

`sources/` contains local resources for `MLLM - PLM Workflow`: demo inputs, precomputed demo outputs, PLM inference modules, local model folders, and Hugging Face cache directories.

Large model files and cache directories are ignored by Git. They must be placed manually on each machine that runs the real pipeline.

## Expected Structure

```text
sources/
|-- input_images/
|-- outputs/
|-- plm_inference/
|-- mllm_models/
|-- plm_models/
|-- hf_cache/
`-- README.md
```

## Input Images

Demo images live under:

```text
sources/input_images/
```

Primary demo image:

```text
sources/input_images/example_cxr.jpg
```

## Demo Outputs

Precomputed fallback outputs live under:

```text
sources/outputs/final_whole_system_demo/
```

These support:

- `RADIOLOGY_PIPELINE_MODE=mock`
- frontend fallback exports
- demo review when model files are unavailable

## CheXagent MLLM Models

Findings model folder:

```text
sources/mllm_models/chexagent_findings/
```

Impression model folder:

```text
sources/mllm_models/chexagent_impression/
```

Each CheXagent model folder must include the safetensors shards referenced by its `model.safetensors.index.json`, plus the tokenizer files, config files, and custom model code files required by Transformers with `trust_remote_code=True`.

Expected shard names:

```text
model-00001-of-00003.safetensors
model-00002-of-00003.safetensors
model-00003-of-00003.safetensors
```

Run this check from `backend/`:

```powershell
python mllm_worker\check_model_files.py
```

## PLM / RadBERT Models

PLM model folders:

```text
sources/plm_models/radbert_findings_model/
sources/plm_models/radbert_impression_model/
```

Each folder must include model weights and tokenizer/config files. At minimum, the backend checks for:

```text
model.safetensors
```

## PLM Inference Modules

Reusable PLM extraction code lives under:

```text
sources/plm_inference/
```

These modules are imported by the backend PLM service after the main backend environment is prepared.

## Hugging Face Cache

The local Hugging Face cache may live under:

```text
sources/hf_cache/
```

This folder is ignored by Git and can be regenerated locally.

## Git Policy

The following local folders are intentionally ignored:

- `sources/hf_cache/`
- `sources/models/`
- `sources/mllm_models/`
- `sources/plm_models/`

Do not commit large model files such as `.safetensors`, `.bin`, `.pt`, `.pth`, `.ckpt`, or `.onnx`.
