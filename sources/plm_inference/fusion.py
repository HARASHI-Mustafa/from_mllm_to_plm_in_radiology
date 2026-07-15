"""
Fusion logic for section-aware PLM inference.

This module combines predictions from:
- Impression PLM extractor
- Findings PLM extractor

The goal is not to make a final autonomous diagnosis.
The goal is to produce structured decision-support outputs:
- final finding state
- evidence source
- agreement status
- confidence level
- review recommendation
"""

from typing import Any, Dict, List, Optional

from plm_inference.labels import ABNORMAL_LABELS, LABEL_COLUMNS


VALID_STATES = {
    "not_mentioned",
    "absent",
    "uncertain",
    "present",
}


def get_state(
    section_output: Optional[Dict[str, Dict[str, Any]]],
    label: str,
) -> str:
    """
    Safely get the predicted state for one label from a section output.

    If the section output is missing or the label is unavailable,
    return 'not_mentioned'.
    """
    if section_output is None:
        return "not_mentioned"

    if label not in section_output:
        return "not_mentioned"

    state = section_output[label].get("state", "not_mentioned")

    if state not in VALID_STATES:
        return "not_mentioned"

    return state


def get_probability(
    section_output: Optional[Dict[str, Dict[str, Any]]],
    label: str,
) -> Optional[float]:
    """
    Safely get the predicted probability for one label from a section output.
    """
    if section_output is None:
        return None

    if label not in section_output:
        return None

    probability = section_output[label].get("probability", None)

    if probability is None:
        return None

    return float(probability)


def fuse_two_states(
    impression_state: str,
    findings_state: str,
) -> Dict[str, Any]:
    """
    Fuse one Impression state and one Findings state.

    States:
    - not_mentioned
    - absent
    - uncertain
    - present

    Fusion principles:
    1. If both sections agree, keep the shared state with high confidence.
    2. If only one section contains positive evidence, keep it with medium confidence.
    3. If only one section contains explicit negative evidence, keep it with medium confidence.
    4. If uncertainty is involved, mark final state as uncertain and recommend review.
    5. If one section says present and the other says absent, mark conflict and recommend review.
    """

    if impression_state not in VALID_STATES:
        impression_state = "not_mentioned"

    if findings_state not in VALID_STATES:
        findings_state = "not_mentioned"

    # Case 1: agreement
    if impression_state == findings_state:
        return {
            "final_state": impression_state,
            "source": "impression+findings",
            "agreement": "agree",
            "confidence_level": "high",
            "review_recommended": False,
        }

    # Case 2: direct contradiction
    if {impression_state, findings_state} == {"present", "absent"}:
        return {
            "final_state": "conflict",
            "source": "impression+findings",
            "agreement": "contradiction_present_vs_absent",
            "confidence_level": "low",
            "review_recommended": True,
        }

    # Case 3: uncertainty in one or both sections
    if "uncertain" in {impression_state, findings_state}:
        return {
            "final_state": "uncertain",
            "source": "impression+findings",
            "agreement": "uncertainty_or_partial_conflict",
            "confidence_level": "low",
            "review_recommended": True,
        }

    # Case 4: Impression gives positive evidence, Findings does not mention it
    if impression_state == "present" and findings_state == "not_mentioned":
        return {
            "final_state": "present",
            "source": "impression",
            "agreement": "single_section_positive",
            "confidence_level": "medium",
            "review_recommended": False,
        }

    # Case 5: Findings gives positive evidence, Impression does not mention it
    if findings_state == "present" and impression_state == "not_mentioned":
        return {
            "final_state": "present",
            "source": "findings",
            "agreement": "single_section_positive",
            "confidence_level": "medium",
            "review_recommended": False,
        }

    # Case 6: Impression gives negative evidence, Findings does not mention it
    if impression_state == "absent" and findings_state == "not_mentioned":
        return {
            "final_state": "absent",
            "source": "impression",
            "agreement": "single_section_negative",
            "confidence_level": "medium",
            "review_recommended": False,
        }

    # Case 7: Findings gives negative evidence, Impression does not mention it
    if findings_state == "absent" and impression_state == "not_mentioned":
        return {
            "final_state": "absent",
            "source": "findings",
            "agreement": "single_section_negative",
            "confidence_level": "medium",
            "review_recommended": False,
        }

    # Fallback: conservative uncertainty
    return {
        "final_state": "uncertain",
        "source": "impression+findings",
        "agreement": "uncertainty_or_partial_conflict",
        "confidence_level": "low",
        "review_recommended": True,
    }


def fuse_impression_and_findings(
    impression_output: Optional[Dict[str, Dict[str, Any]]],
    findings_output: Optional[Dict[str, Dict[str, Any]]],
    apply_consistency_rules: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """
    Fuse all labels from Impression and Findings PLM outputs.

    Returns one structured dictionary per finding.
    """
    fused: Dict[str, Dict[str, Any]] = {}

    for label in LABEL_COLUMNS:
        impression_state = get_state(impression_output, label)
        findings_state = get_state(findings_output, label)

        fusion = fuse_two_states(
            impression_state=impression_state,
            findings_state=findings_state,
        )

        fused[label] = {
            "final_state": fusion["final_state"],
            "impression_state": impression_state,
            "findings_state": findings_state,
            "impression_probability": get_probability(impression_output, label),
            "findings_probability": get_probability(findings_output, label),
            "source": fusion["source"],
            "agreement": fusion["agreement"],
            "confidence_level": fusion["confidence_level"],
            "review_recommended": fusion["review_recommended"],
        }

    if apply_consistency_rules:
        fused = apply_no_finding_consistency_rule(fused)

    return fused


def apply_no_finding_consistency_rule(
    fused: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    If any abnormal finding is present, No Finding should not remain present.

    Example of incoherent output:
    - No Finding = present
    - Edema = present

    Corrected output:
    - No Finding = not_mentioned
    - Edema = present
    """

    if "No Finding" not in fused:
        return fused

    present_abnormal_labels = [
        label
        for label in ABNORMAL_LABELS
        if fused.get(label, {}).get("final_state") == "present"
    ]

    no_finding_state = fused["No Finding"].get("final_state", "not_mentioned")

    if len(present_abnormal_labels) > 0 and no_finding_state == "present":
        fused["No Finding"]["final_state"] = "not_mentioned"
        fused["No Finding"]["agreement"] = "corrected_by_consistency_rule"
        fused["No Finding"]["source"] = "rule_based_postprocessing"
        fused["No Finding"]["confidence_level"] = "medium"
        fused["No Finding"]["review_recommended"] = False
        fused["No Finding"]["correction_note"] = (
            "No Finding changed from present to not_mentioned because "
            "one or more abnormal findings were present."
        )
        fused["No Finding"]["present_abnormal_labels"] = present_abnormal_labels

    return fused


def summarize_fused_output(
    fused: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Create a case-level summary from fused label-level outputs.

    This summary is useful for:
    - displaying results,
    - batch metadata,
    - future MLLM input preparation.
    """

    present_labels: List[str] = []
    uncertain_labels: List[str] = []
    conflict_labels: List[str] = []
    review_labels: List[str] = []

    for label in LABEL_COLUMNS:
        item = fused[label]
        final_state = item["final_state"]

        if final_state == "present":
            present_labels.append(label)

        if final_state == "uncertain":
            uncertain_labels.append(label)

        if final_state == "conflict":
            conflict_labels.append(label)

        if item.get("review_recommended", False):
            review_labels.append(label)

    if len(conflict_labels) > 0:
        global_status = "possible_section_conflict"
    elif len(review_labels) > 0:
        global_status = "review_recommended"
    elif len(present_labels) > 0 or len(uncertain_labels) > 0:
        global_status = "abnormal_or_uncertain_report_findings"
    else:
        global_status = "no_major_report_finding_detected"

    return {
        "global_status": global_status,
        "present_labels": present_labels,
        "uncertain_labels": uncertain_labels,
        "conflict_labels": conflict_labels,
        "review_labels": review_labels,
        "n_present_labels": len(present_labels),
        "n_uncertain_labels": len(uncertain_labels),
        "n_conflict_labels": len(conflict_labels),
        "n_review_labels": len(review_labels),
    }


def fused_output_to_rows(
    case_id: Any,
    fused: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Convert fused output dictionary into one row per label.

    This is useful for creating batch_comparison_df.
    """
    rows: List[Dict[str, Any]] = []

    for label in LABEL_COLUMNS:
        item = fused[label]

        rows.append(
            {
                "case_id": case_id,
                "finding": label,
                "plm_final_state": item["final_state"],
                "plm_impression_state": item["impression_state"],
                "plm_findings_state": item["findings_state"],
                "source": item["source"],
                "agreement": item["agreement"],
                "confidence_level": item["confidence_level"],
                "review_recommended": item["review_recommended"],
                "impression_probability": item["impression_probability"],
                "findings_probability": item["findings_probability"],
            }
        )

    return rows