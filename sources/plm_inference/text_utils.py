"""
Text utility functions for section-aware PLM inference.

These functions are used to:
- decide whether a report section is valid,
- clean text values,
- detect multi-timepoint reports.
"""

import re
from typing import Any, List, Optional


INVALID_TEXT_PLACEHOLDERS = {
    "nan",
    "none",
    "null",
    "na",
    "n/a",
    "/",
    "\\",
    "-",
    "--",
    ".",
    "...",
}


def valid_text(value: Any) -> bool:
    """
    Return True if a value contains useful report text.

    This rejects empty values and placeholder symbols such as:
    '/', '-', '.', 'nan', 'none', 'null'.

    This is important because some CheXpert Plus sections contain
    placeholder symbols instead of real Findings or Impression text.
    """
    if value is None:
        return False

    text = str(value).strip()

    if text == "":
        return False

    if text.lower() in INVALID_TEXT_PLACEHOLDERS:
        return False

    # Reject text that contains no letters or numbers.
    if not re.search(r"[A-Za-z0-9]", text):
        return False

    return True


def clean_text_or_none(value: Any) -> Optional[str]:
    """
    Return a cleaned text string if valid, otherwise None.
    """
    if not valid_text(value):
        return None

    return str(value).strip()


def detect_timepoints(text: Optional[str]) -> List[str]:
    """
    Detect timepoint markers inside a report.

    Example detected patterns:
    - 02:06
    - 07:52
    - 13:46

    This is useful because some reports describe multiple timepoints,
    while the future MLLM phase may receive only one image.
    """
    if not valid_text(text):
        return []

    text = str(text)

    # Matches simple time patterns like 02:06, 7:52, 13:46.
    timepoints = re.findall(r"\b\d{1,2}:\d{2}\b", text)

    return timepoints


def is_multi_timepoint_report(text: Optional[str]) -> bool:
    """
    Return True if the report contains more than one detected timepoint.
    """
    return len(detect_timepoints(text)) > 1


def combine_report_sections(
    findings_text: Optional[str],
    impression_text: Optional[str],
) -> str:
    """
    Combine Findings and Impression text for metadata checks only.

    The PLM models still process Findings and Impression separately.
    This combined text is useful for detecting multi-timepoint reports.
    """
    parts = []

    findings_clean = clean_text_or_none(findings_text)
    impression_clean = clean_text_or_none(impression_text)

    if findings_clean is not None:
        parts.append(findings_clean)

    if impression_clean is not None:
        parts.append(impression_clean)

    return "\n\n".join(parts)