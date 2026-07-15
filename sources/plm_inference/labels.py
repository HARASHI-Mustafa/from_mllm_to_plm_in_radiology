"""
Label definitions for section-aware PLM inference.

The task uses CheXpert-style radiology findings with four states:
0 = not_mentioned
1 = absent
2 = uncertain
3 = present
"""

from typing import Dict, List


LABEL_COLUMNS: List[str] = [
    "No Finding",
    "Enlarged Cardiomediastinum",
    "Cardiomegaly",
    "Lung Opacity",
    "Lung Lesion",
    "Edema",
    "Consolidation",
    "Pneumonia",
    "Atelectasis",
    "Pneumothorax",
    "Pleural Effusion",
    "Pleural Other",
    "Fracture",
    "Support Devices",
]


STATE_ID_TO_NAME: Dict[int, str] = {
    0: "not_mentioned",
    1: "absent",
    2: "uncertain",
    3: "present",
}


STATE_NAME_TO_ID: Dict[str, int] = {
    value: key for key, value in STATE_ID_TO_NAME.items()
}


ABNORMAL_LABELS: List[str] = [
    label for label in LABEL_COLUMNS
    if label != "No Finding"
]


NUM_LABELS: int = len(LABEL_COLUMNS)
NUM_CLASSES: int = len(STATE_ID_TO_NAME)