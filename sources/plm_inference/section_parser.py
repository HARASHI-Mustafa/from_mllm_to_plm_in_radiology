"""
Raw report section parser for section-aware PLM inference.

This module extracts Findings and Impression sections from a raw
radiology report text.

It supports the future reusable workflow where the input may be:
- already separated sections, or
- a full raw report.

Important design choice:
SUMMARY is NOT treated as Impression because in CheXpert Plus it often
contains severity/action labels such as:
"4-POSSIBLE SIGNIFICANT FINDINGS, MAY NEED ACTION"

Those summary lines are metadata, not the radiology Impression text.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from plm_inference.text_utils import clean_text_or_none, valid_text


# Main clinical section headings.
SECTION_ALIASES = {
    "history": [
        "history",
        "clinical history",
        "indication",
        "clinical indication",
        "reason for exam",
        "reason for examination",
    ],
    "comparison": [
        "comparison",
        "comparisons",
        "compared to",
    ],
    "technique": [
        "technique",
        "procedure",
        "view",
        "views",
        "portable chest",
        "chest portable",
        "chest single view",
        "chest 2 views",
        "chest two views",
        "pa and lateral chest",
    ],
    "findings": [
        "findings",
        "radiographic findings",
        "chest findings",
    ],
    "impression": [
        "impression",
        "impressions",
        "conclusion",
        "conclusions",
        "assessment",
    ],
}


# These are boundaries or metadata headings, not clinical content sections.
# They are used to stop extraction.
STOP_HEADINGS = [
    "end of impression",
    "summary",
    "accession number",
    "addendum begins",
    "addendum ends",
    "end of addendum",
    "narrative",
]


BOILERPLATE_START_PATTERNS = [
    r"\bI have personally reviewed\b",
    r"\bThis report has been anonymized\b",
    r"\bAll dates are offset\b",
    r"\bACCESSION NUMBER\b",
    r"\bEND OF IMPRESSION\b",
    r"\bSUMMARY\s*:",
    r"\bEnd of Addendum\b",
]


def normalize_whitespace(text: str) -> str:
    """
    Normalize line endings and excessive spaces while preserving line structure.
    """
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_heading_regex() -> re.Pattern:
    """
    Build regex pattern for known section headings and stop headings.

    Examples detected:
    FINDINGS:
    IMPRESSION:
    END OF IMPRESSION:
    SUMMARY:
    ACCESSION NUMBER:
    """
    heading_terms = []

    for aliases in SECTION_ALIASES.values():
        heading_terms.extend(aliases)

    heading_terms.extend(STOP_HEADINGS)

    # Sort longest first to avoid partial matching.
    heading_terms = sorted(set(heading_terms), key=len, reverse=True)

    escaped_terms = [re.escape(term) for term in heading_terms]

    pattern = (
        r"(?im)"
        r"(^|\n)"
        r"\s*"
        r"("
        + "|".join(escaped_terms)
        + r")"
        r"\s*"
        r"[:\-]?"
        r"\s*"
        r"(?=\n|$|[A-Z0-9])"
    )

    return re.compile(pattern)


HEADING_REGEX = build_heading_regex()


def canonicalize_heading(heading: str) -> Optional[str]:
    """
    Convert a heading variant to a canonical section name.

    SUMMARY and ACCESSION NUMBER are returned as stop sections.
    """
    heading_norm = heading.strip().lower()

    for stop_heading in STOP_HEADINGS:
        if heading_norm == stop_heading:
            return "stop"

    for canonical, aliases in SECTION_ALIASES.items():
        if heading_norm in aliases:
            return canonical

    return None


def trim_boilerplate(content: str) -> str:
    """
    Remove trailing boilerplate or metadata from extracted section text.
    """
    if not valid_text(content):
        return ""

    text = normalize_whitespace(content)

    cut_positions = []

    for pattern in BOILERPLATE_START_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            cut_positions.append(match.start())

    if len(cut_positions) > 0:
        text = text[: min(cut_positions)].strip()

    return text.strip()


def find_section_headings(text: str) -> List[Dict[str, Any]]:
    """
    Find section and stop headings in a raw report.
    """
    if not valid_text(text):
        return []

    text = normalize_whitespace(text)

    matches = []

    for match in HEADING_REGEX.finditer(text):
        heading = match.group(2)
        section = canonicalize_heading(heading)

        if section is None:
            continue

        matches.append(
            {
                "section": section,
                "heading": heading,
                "start": match.start(),
                "content_start": match.end(),
            }
        )

    unique = []
    seen_positions = set()

    for item in matches:
        if item["start"] not in seen_positions:
            unique.append(item)
            seen_positions.add(item["start"])

    unique = sorted(unique, key=lambda x: x["start"])

    return unique


def extract_sections_from_headings(
    text: str,
    headings: List[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Extract section contents using detected heading positions.

    Stop headings are not saved as clinical sections. They only mark
    the end of the previous section.
    """
    sections: Dict[str, str] = {}

    if len(headings) == 0:
        return sections

    text = normalize_whitespace(text)

    for idx, heading_info in enumerate(headings):
        section = heading_info["section"]

        if section == "stop":
            continue

        content_start = heading_info["content_start"]

        if idx + 1 < len(headings):
            content_end = headings[idx + 1]["start"]
        else:
            content_end = len(text)

        content = text[content_start:content_end].strip()
        content = trim_boilerplate(content)

        if valid_text(content):
            if section in sections and valid_text(sections[section]):
                sections[section] = sections[section].strip() + "\n\n" + content
            else:
                sections[section] = content

    return sections


def fallback_extract_impression_from_end(text: str) -> Optional[str]:
    """
    Conservative fallback when no explicit Impression heading is found.

    This is intentionally limited. If a report is long and unstructured,
    we prefer not to guess.
    """
    if not valid_text(text):
        return None

    text = normalize_whitespace(text)
    lines = [line.strip() for line in text.split("\n") if valid_text(line)]

    if len(lines) == 0:
        return None

    if len(lines) > 8:
        return None

    last_line = lines[-1]

    if 5 <= len(last_line.split()) <= 60:
        return trim_boilerplate(last_line)

    return None


def parse_report_sections(
    raw_report_text: Optional[str],
    use_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Parse a raw full radiology report into sections.

    Returns:
    - findings_text
    - impression_text
    - other_sections
    - detected_sections
    - parser_status
    """
    raw_clean = clean_text_or_none(raw_report_text)

    if raw_clean is None:
        return {
            "findings_text": None,
            "impression_text": None,
            "other_sections": {},
            "detected_sections": [],
            "n_detected_sections": 0,
            "parser_status": "empty_or_invalid_report",
        }

    text = normalize_whitespace(raw_clean)

    headings = find_section_headings(text)
    extracted = extract_sections_from_headings(text, headings)

    findings_text = clean_text_or_none(extracted.get("findings"))
    impression_text = clean_text_or_none(extracted.get("impression"))

    if impression_text is None and use_fallback:
        impression_text = fallback_extract_impression_from_end(text)

    other_sections = {
        section: content
        for section, content in extracted.items()
        if section not in ["findings", "impression"]
    }

    detected_sections = list(extracted.keys())

    if findings_text is not None and impression_text is not None:
        parser_status = "found_findings_and_impression"
    elif findings_text is not None and impression_text is None:
        parser_status = "found_findings_only"
    elif findings_text is None and impression_text is not None:
        parser_status = "found_impression_only"
    elif len(detected_sections) > 0:
        parser_status = "found_other_sections_only"
    else:
        parser_status = "no_known_sections_found"

    return {
        "findings_text": findings_text,
        "impression_text": impression_text,
        "other_sections": other_sections,
        "detected_sections": detected_sections,
        "n_detected_sections": len(detected_sections),
        "parser_status": parser_status,
    }


def parse_report_sections_simple(
    raw_report_text: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Return only:
    findings_text, impression_text
    """
    parsed = parse_report_sections(raw_report_text)
    return parsed["findings_text"], parsed["impression_text"]