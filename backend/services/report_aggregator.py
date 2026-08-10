"""
Combines deterministic backend validation with Vision AI results into one
unified ComplianceReport. This is the only place that knows about both
sources -- the frontend just renders whatever comes out of here.
"""

import json

from config import RULES_PATH
from models import ComplianceReport, RuleResult, TechnicalValidation
from services.safe_zone import evaluate_safe_zone

RULE_META_CACHE = None


def _rule_meta() -> dict:
    global RULE_META_CACHE
    if RULE_META_CACHE is None:
        with open(RULES_PATH, "r") as f:
            rules = json.load(f)["rules"]
        RULE_META_CACHE = {r["id"]: r for r in rules}
    return RULE_META_CACHE


def _build_vision_rule_result(rule_id: str, ai_output: dict) -> RuleResult:
    meta = _rule_meta().get(rule_id, {})
    return RuleResult(
        id=rule_id,
        title=meta.get("title", rule_id),
        category=meta.get("category", "General"),
        severity=meta.get("severity", "Medium"),
        status=ai_output.get("status", "WARNING"),
        confidence=float(ai_output.get("confidence", 0.5)),
        reason=ai_output.get("reason", ""),
        evidence=ai_output.get("evidence", []) or [],
        recommendation=ai_output.get("recommendation"),
        source="vision_ai",
    )


def build_report(
    filename: str,
    asset_type: str,
    technical_validation: TechnicalValidation,
    ai_response: dict,
) -> ComplianceReport:
    ai_rules = ai_response.get("rules", {})
    detected_elements = ai_response.get("detected_elements", {})

    visual_compliance = []
    for rule_id, meta in _rule_meta().items():
        if meta["evaluation_type"] not in ("vision", "vision+backend"):
            continue

        if rule_id == "SAFE_ZONE":
            result = evaluate_safe_zone(detected_elements, ai_rules.get("SAFE_ZONE"))
        else:
            ai_output = ai_rules.get(rule_id)
            if ai_output is None:
                result = RuleResult(
                    id=rule_id,
                    title=meta["title"],
                    category=meta["category"],
                    severity=meta["severity"],
                    status="WARNING",
                    confidence=0.0,
                    reason="Vision AI did not return a result for this rule.",
                    evidence=[],
                    recommendation="Re-run the review.",
                    source="vision_ai",
                )
            else:
                result = _build_vision_rule_result(rule_id, ai_output)

        visual_compliance.append(result)

    all_results = [
        technical_validation.dimension_check,
        technical_validation.aspect_ratio_check,
    ] + visual_compliance

    fail_count = sum(1 for r in all_results if r.status == "FAIL")
    warning_count = sum(1 for r in all_results if r.status == "WARNING")
    pass_count = sum(1 for r in all_results if r.status == "PASS")

    critical_fail = any(r.status == "FAIL" and r.severity == "Critical" for r in all_results)
    if critical_fail or fail_count > 0:
        overall_status = "FAIL"
    elif warning_count > 0:
        overall_status = "WARNING"
    else:
        overall_status = "PASS"

    return ComplianceReport(
        overall_status=overall_status,
        asset_type=asset_type,
        filename=filename,
        technical_validation=technical_validation,
        visual_compliance=visual_compliance,
        summary={
            "total_checks": len(all_results),
            "passed": pass_count,
            "warnings": warning_count,
            "failed": fail_count,
        },
    )
