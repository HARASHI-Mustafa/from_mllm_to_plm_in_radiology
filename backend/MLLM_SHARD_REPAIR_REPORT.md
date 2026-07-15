# MLLM Shard Placement Note

This note is retained as historical setup documentation for CheXagent model shard placement.

The current real pipeline expects each local CheXagent model folder to contain the canonical shard names referenced by its `model.safetensors.index.json`.

## Required Layout

```text
sources/mllm_models/chexagent_findings/
|-- model-00001-of-00003.safetensors
|-- model-00002-of-00003.safetensors
`-- model-00003-of-00003.safetensors

sources/mllm_models/chexagent_impression/
|-- model-00001-of-00003.safetensors
|-- model-00002-of-00003.safetensors
`-- model-00003-of-00003.safetensors
```

Each folder must also include tokenizer files, config files, custom model code files, and `model.safetensors.index.json`.

## Verification

Run from `backend/`:

```powershell
python mllm_worker\check_model_files.py
```

The real pipeline should not be used until this check passes and `GET /api/pipeline/status` reports `real_pipeline_ready: true`.

## Git Policy

The model folders and `.safetensors` files are intentionally ignored by Git. Do not commit model weights or Hugging Face cache files to the public repository.
