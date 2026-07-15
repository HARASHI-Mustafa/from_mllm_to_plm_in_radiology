"""
Model loading and prediction utilities for section-aware PLM inference.

This module loads a full fine-tuned RadBERT multi-finding classifier
and applies it to Findings or Impression text sections.

The expected saved model folder is a Hugging Face-style folder such as:

outputs/plm_results/track_a_full_finetuning/radbert_impression_track_a_full/best_model

or:

outputs/plm_results/track_e_findings_only/radbert_findings_only_full/best_model
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import torch
from torch import nn
from transformers import AutoModel, AutoTokenizer

try:
    from safetensors.torch import load_file as load_safetensors
    SAFETENSORS_AVAILABLE = True
except Exception:
    SAFETENSORS_AVAILABLE = False

from plm_inference.labels import LABEL_COLUMNS, NUM_CLASSES, STATE_ID_TO_NAME
from plm_inference.text_utils import clean_text_or_none


class MultiFindingClassifier(nn.Module):
    """
    Multi-finding classifier for CheXpert-style labels.

    Architecture:
    - Transformer backbone, e.g. RadBERT.
    - CLS token representation.
    - Dropout.
    - Linear classifier producing:
      num_findings × num_classes_per_finding logits.

    Output shape:
    batch_size × num_findings × num_classes_per_finding
    """

    def __init__(
        self,
        model_name: str,
        num_findings: int = len(LABEL_COLUMNS),
        num_classes_per_finding: int = NUM_CLASSES,
        dropout: float = 0.10,
    ):
        super().__init__()

        self.num_findings = num_findings
        self.num_classes_per_finding = num_classes_per_finding

        self.backbone = AutoModel.from_pretrained(model_name)

        hidden_size = self.backbone.config.hidden_size

        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(
            hidden_size,
            num_findings * num_classes_per_finding,
        )

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        outputs = self.backbone(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )

        pooled = outputs.last_hidden_state[:, 0, :]
        pooled = self.dropout(pooled)

        logits_flat = self.classifier(pooled)

        logits = logits_flat.view(
            -1,
            self.num_findings,
            self.num_classes_per_finding,
        )

        return logits


def get_device(device: Optional[Union[str, torch.device]] = None) -> torch.device:
    """
    Return the device used for inference.

    If device is None:
    - use CUDA if available,
    - otherwise use CPU.
    """
    if device is not None:
        return torch.device(device)

    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_state_dict_from_model_dir(
    model_dir: Union[str, Path],
    device: Optional[Union[str, torch.device]] = None,
) -> Dict[str, torch.Tensor]:
    """
    Load model weights from a saved model directory.

    Supported files:
    - model.safetensors
    - pytorch_model.bin
    """
    model_dir = Path(model_dir)
    device = get_device(device)

    safetensors_path = model_dir / "model.safetensors"
    pytorch_bin_path = model_dir / "pytorch_model.bin"

    if safetensors_path.exists():
        if not SAFETENSORS_AVAILABLE:
            raise ImportError(
                "safetensors is required to load model.safetensors. "
                "Install it with: pip install safetensors"
            )

        print(f"Loading weights from: {safetensors_path}")
        return load_safetensors(str(safetensors_path), device=str(device))

    if pytorch_bin_path.exists():
        print(f"Loading weights from: {pytorch_bin_path}")
        return torch.load(pytorch_bin_path, map_location=device)

    raise FileNotFoundError(
        f"No model weights found in {model_dir}. "
        "Expected model.safetensors or pytorch_model.bin."
    )


def load_full_finetuned_model(
    model_dir: Union[str, Path],
    base_model_name: str = "StanfordAIMI/RadBERT",
    device: Optional[Union[str, torch.device]] = None,
    dropout: float = 0.10,
) -> Tuple[nn.Module, Any]:
    """
    Load a full fine-tuned multi-finding PLM model and tokenizer.

    Parameters
    ----------
    model_dir:
        Path to the saved best_model/ directory.

    base_model_name:
        Hugging Face base model name used to recreate the architecture.

    device:
        "cuda", "cpu", or None.

    dropout:
        Dropout used in the classifier architecture.
        Must match training architecture.

    Returns
    -------
    model, tokenizer
    """
    model_dir = Path(model_dir)
    device = get_device(device)

    if not model_dir.exists():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    try:
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    except Exception:
        print(
            "Tokenizer not found in model folder. "
            f"Falling back to base tokenizer: {base_model_name}"
        )
        tokenizer = AutoTokenizer.from_pretrained(base_model_name)

    model = MultiFindingClassifier(
        model_name=base_model_name,
        num_findings=len(LABEL_COLUMNS),
        num_classes_per_finding=NUM_CLASSES,
        dropout=dropout,
    )

    state_dict = load_state_dict_from_model_dir(
        model_dir=model_dir,
        device=device,
    )

    missing_keys, unexpected_keys = model.load_state_dict(
        state_dict,
        strict=False,
    )

    print("Missing keys:", missing_keys)
    print("Unexpected keys:", unexpected_keys)

    if len(missing_keys) > 0:
        raise RuntimeError(
            "Some model weights are missing. "
            f"Missing keys: {missing_keys}"
        )

    if len(unexpected_keys) > 0:
        raise RuntimeError(
            "Some unexpected model weights were found. "
            f"Unexpected keys: {unexpected_keys}"
        )

    model.to(device)
    model.eval()

    return model, tokenizer


@torch.no_grad()
def predict_texts_batch(
    texts: List[Optional[str]],
    model: nn.Module,
    tokenizer: Any,
    device: Optional[Union[str, torch.device]] = None,
    batch_size: int = 16,
    max_length: int = 256,
) -> List[Optional[Dict[str, Dict[str, Any]]]]:
    """
    Predict structured finding states for a batch of texts.

    Invalid or missing texts return None.

    Returns
    -------
    A list with the same length as input texts.

    Each valid item has this structure:

    {
        "Cardiomegaly": {
            "state": "present",
            "class_id": 3,
            "probability": 0.97,
            "class_probabilities": {
                "not_mentioned": ...,
                "absent": ...,
                "uncertain": ...,
                "present": ...
            }
        },
        ...
    }
    """
    device = get_device(device)
    model.to(device)
    model.eval()

    outputs: List[Optional[Dict[str, Dict[str, Any]]]] = [None] * len(texts)

    valid_indices = []
    valid_texts = []

    for idx, value in enumerate(texts):
        cleaned = clean_text_or_none(value)
        if cleaned is not None:
            valid_indices.append(idx)
            valid_texts.append(cleaned)

    for start in range(0, len(valid_indices), batch_size):
        end = start + batch_size

        batch_indices = valid_indices[start:end]
        batch_texts = valid_texts[start:end]

        enc = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )

        input_ids = enc["input_ids"].to(device)
        attention_mask = enc["attention_mask"].to(device)

        logits = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )

        probs = torch.softmax(logits, dim=-1).detach().cpu()
        pred_ids = probs.argmax(dim=-1)

        for local_idx, original_idx in enumerate(batch_indices):
            section_output: Dict[str, Dict[str, Any]] = {}

            for label_idx, label in enumerate(LABEL_COLUMNS):
                pred_class = int(pred_ids[local_idx, label_idx].item())
                pred_state = STATE_ID_TO_NAME[pred_class]

                section_output[label] = {
                    "state": pred_state,
                    "class_id": pred_class,
                    "probability": float(probs[local_idx, label_idx, pred_class].item()),
                    "class_probabilities": {
                        STATE_ID_TO_NAME[class_id]: float(
                            probs[local_idx, label_idx, class_id].item()
                        )
                        for class_id in range(NUM_CLASSES)
                    },
                }

            outputs[original_idx] = section_output

    return outputs


def predict_one_text(
    text: Optional[str],
    model: nn.Module,
    tokenizer: Any,
    device: Optional[Union[str, torch.device]] = None,
    max_length: int = 256,
) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Predict structured finding states for one text section.
    """
    return predict_texts_batch(
        texts=[text],
        model=model,
        tokenizer=tokenizer,
        device=device,
        batch_size=1,
        max_length=max_length,
    )[0]