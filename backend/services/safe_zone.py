"""
Deterministic 7% safe-margin calculation from bounding boxes.

The Vision AI detects and returns bounding boxes for critical elements
(SAFE_ZONE_INSTRUCTION in prompt_builder.py); this module does the actual
geometry, per rules.json's evaluation_instructions for SAFE_ZONE: "The
backend will calculate a 7% safe margin from each image edge and verify
whether every bounding box lies completely inside this region."

Boxes are expected on Gemini's standard 0-1000 normalized scale, as
[ymin, xmin, ymax, xmax].
"""

from typing import Optional

from config import SAFE_ZONE_MARGIN_PERCENT
from models import RuleResult

SCALE = 1000.0
MARGIN = SAFE_ZONE_MARGIN_PERCENT / 100.0 * SCALE
SAFE_MIN = MARGIN
SAFE_MAX = SCALE - MARGIN


def _box_violations(name: str, box: list) -> list:
    """Returns a list of human-readable violation strings for one box, or [] if safe."""
    if not box or len(box) != 4:
        return []
    ymin, xmin, ymax, xmax = box
    violations = []
    if xmin < SAFE_MIN:
        violations.append(f"{name} crosses the left safe margin")
    if xmax > SAFE_MAX:
        violations.append(f"{name} crosses the right safe margin")
    if ymin < SAFE_MIN:
        violations.append(f"{name} crosses the top safe margin")
    if ymax > SAFE_MAX:
        violations.append(f"{name} crosses the bottom safe margin")
    return violations


def evaluate_safe_zone(detected_elements: dict, ai_fallback: Optional[dict]) -> RuleResult:
    """
    Computes the SAFE_ZONE result deterministically from detected bounding
    boxes. Falls back to the Vision AI's own qualitative SAFE_ZONE judgement
    (still vision-sourced, just not backend-verified) only if no usable
    bounding boxes were returned at all.
    """
    detected_elements = detected_elements or {}

    element_map = {
        "primary_subject": detected_elements.get("primary_subject"),
        "title": detected_elements.get("title"),
        "brand_logo": detected_elements.get("brand_logo"),
        "sponsor_logo": detected_elements.get("sponsor_logo"),
    }
    faces = detected_elements.get("faces") or []

    all_violations = []
    checked_any = False

    for name, box in element_map.items():
        if box:
            checked_any = True
            all_violations.extend(_box_violations(name.replace("_", " "), box))

    for i, box in enumerate(faces):
        if box:
            checked_any = True
            all_violations.extend(_box_violations(f"face #{i + 1}", box))

    if not checked_any:
        # No bounding boxes returned at all -- fall back to the AI's own
        # qualitative read rather than fabricating a result.
        if ai_fallback:
            return RuleResult(
                id="SAFE_ZONE",
                title="Safe Zone Compliance",
                category="Layout",
                severity="Critical",
                status=ai_fallback.get("status", "WARNING"),
                confidence=float(ai_fallback.get("confidence", 0.5)),
                reason=ai_fallback.get("reason", "No bounding boxes were detected; relying on the model's qualitative assessment."),
                evidence=ai_fallback.get("evidence", []),
                recommendation=ai_fallback.get("recommendation"),
                source="vision_ai",
            )
        return RuleResult(
            id="SAFE_ZONE",
            title="Safe Zone Compliance",
            category="Layout",
            severity="Critical",
            status="WARNING",
            confidence=0.3,
            reason="No critical elements could be detected to evaluate the safe zone.",
            evidence=[],
            recommendation="Manually verify that the subject, title and branding sit within the 7% safe margin.",
            source="vision_ai",
        )

    status = "FAIL" if all_violations else "PASS"
    reason = (
        f"All detected critical elements lie within the {SAFE_ZONE_MARGIN_PERCENT}% safe margin."
        if status == "PASS"
        else f"{len(all_violations)} element(s) cross the {SAFE_ZONE_MARGIN_PERCENT}% safe margin: "
        + "; ".join(all_violations)
        + "."
    )

    return RuleResult(
        id="SAFE_ZONE",
        title="Safe Zone Compliance",
        category="Layout",
        severity="Critical",
        status=status,
        confidence=1.0,
        reason=reason,
        evidence=all_violations if all_violations else ["all critical elements within safe margin"],
        recommendation=None if status == "PASS" else "Move the flagged element(s) further away from the image edges.",
        source="vision_ai+backend",
    )
