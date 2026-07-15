import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import (
    LATEST_OUTPUTS_DIR,
    MOCK_GENERATED_REPORT_TXT,
    MOCK_OUTPUT_JSON,
    MOCK_REPORT_MD,
    MOCK_STRUCTURED_CSV,
    RUN_OUTPUTS_DIR,
)


LATEST_JSON = LATEST_OUTPUTS_DIR / "decision_support_output.json"
LATEST_CSV = LATEST_OUTPUTS_DIR / "structured_findings.csv"
LATEST_MARKDOWN = LATEST_OUTPUTS_DIR / "decision_support_report.md"
LATEST_GENERATED_REPORT = LATEST_OUTPUTS_DIR / "generated_report.txt"


def _latest_or_mock(latest_path: Path, mock_path: Path) -> Path:
    if latest_path.exists():
        return latest_path
    return mock_path


def get_mock_json_path() -> Path:
    return _latest_or_mock(LATEST_JSON, MOCK_OUTPUT_JSON)


def get_structured_csv_path() -> Path:
    return _latest_or_mock(LATEST_CSV, MOCK_STRUCTURED_CSV)


def get_markdown_report_path() -> Path:
    return _latest_or_mock(LATEST_MARKDOWN, MOCK_REPORT_MD)


def get_generated_report_txt_path() -> Path:
    return _latest_or_mock(LATEST_GENERATED_REPORT, MOCK_GENERATED_REPORT_TXT)


def _write_generated_report(path: Path, result: dict[str, Any]) -> None:
    report = result.get("generated_report") or {}
    findings = report.get("findings", "")
    impression = report.get("impression", "")
    combined = report.get("combined") or f"FINDINGS:\n{findings}\n\nIMPRESSION:\n{impression}"
    path.write_text(combined, encoding="utf-8")


def _write_structured_findings_csv(path: Path, result: dict[str, Any]) -> None:
    structured = result.get("structured_findings") or {}
    fieldnames = [
        "label",
        "state",
        "confidence",
        "confidence_level",
        "source",
        "not_mentioned",
        "absent",
        "uncertain",
        "present",
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for label, item in structured.items():
            probabilities = item.get("probabilities") or {}
            writer.writerow({
                "label": label,
                "state": item.get("state", ""),
                "confidence": item.get("confidence", ""),
                "confidence_level": item.get("confidence_level", ""),
                "source": item.get("source", ""),
                "not_mentioned": probabilities.get("not_mentioned", ""),
                "absent": probabilities.get("absent", ""),
                "uncertain": probabilities.get("uncertain", ""),
                "present": probabilities.get("present", ""),
            })


def _write_markdown_report(path: Path, result: dict[str, Any]) -> None:
    case_summary = result.get("case_summary") or {}
    decision_support = result.get("decision_support") or {}
    report = result.get("generated_report") or {}

    lines = [
        "# Decision-Support Report",
        "",
        "## Generated Findings",
        report.get("findings", ""),
        "",
        "## Generated Impression",
        report.get("impression", ""),
        "",
        "## Case Summary",
        f"- Case status: {case_summary.get('case_status', 'unknown')}",
        f"- Active abnormal findings: {', '.join(case_summary.get('active_abnormal_findings') or []) or 'None'}",
        "",
        "## Decision Support",
        f"- Review recommended: {decision_support.get('review_recommended')}",
        f"- Review priority: {decision_support.get('review_priority', 'unknown')}",
        f"- Final note: {decision_support.get('final_note', '')}",
    ]
    reasons = decision_support.get("reasons") or []
    if reasons:
        lines.extend(["", "### Reasons"])
        lines.extend(f"- {reason}" for reason in reasons)
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def save_real_run_artifacts(result: dict[str, Any]) -> dict[str, str]:
    LATEST_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    RUN_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUN_OUTPUTS_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    latest_paths = {
        "json": LATEST_JSON,
        "generated_report": LATEST_GENERATED_REPORT,
        "structured_csv": LATEST_CSV,
        "markdown": LATEST_MARKDOWN,
    }
    run_paths = {
        "json": run_dir / "decision_support_output.json",
        "generated_report": run_dir / "generated_report.txt",
        "structured_csv": run_dir / "structured_findings.csv",
        "markdown": run_dir / "decision_support_report.md",
    }

    for path in [latest_paths["json"], run_paths["json"]]:
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    for path in [latest_paths["generated_report"], run_paths["generated_report"]]:
        _write_generated_report(path, result)
    for path in [latest_paths["structured_csv"], run_paths["structured_csv"]]:
        _write_structured_findings_csv(path, result)
    for path in [latest_paths["markdown"], run_paths["markdown"]]:
        _write_markdown_report(path, result)

    return {
        "latest_json": str(latest_paths["json"]),
        "latest_generated_report": str(latest_paths["generated_report"]),
        "latest_structured_csv": str(latest_paths["structured_csv"]),
        "latest_markdown": str(latest_paths["markdown"]),
        "run_dir": str(run_dir),
    }
