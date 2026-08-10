"""
Pydantic models defining the shape of the unified compliance report.

The frontend does not distinguish between backend-generated checks and
AI-generated checks -- both are instances of RuleResult, merged into one
CheckSection so the report renders uniformly.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class RuleResult(BaseModel):
    id: str
    title: str
    category: str
    severity: str
    status: str  # PASS | WARNING | FAIL
    confidence: float
    reason: str
    evidence: List[str] = Field(default_factory=list)
    recommendation: Optional[str] = None
    source: str  # "backend" | "vision_ai" | "vision_ai+backend"


class TechnicalValidation(BaseModel):
    uploaded_width: int
    uploaded_height: int
    expected_width: int
    expected_height: int
    asset_type: str
    dimension_check: RuleResult
    aspect_ratio_check: RuleResult


class ComplianceReport(BaseModel):
    overall_status: str  # PASS | WARNING | FAIL
    asset_type: str
    filename: str
    technical_validation: TechnicalValidation
    visual_compliance: List[RuleResult]
    summary: dict
