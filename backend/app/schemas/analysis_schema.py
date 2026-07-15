from typing import Any

from pydantic import BaseModel, ConfigDict


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    case_summary: dict[str, Any]
    generated_report: dict[str, Any]
    structured_findings: list[dict[str, Any]]
    decision_support: dict[str, Any]


class PLMTextRequest(BaseModel):
    findings: str
    impression: str
