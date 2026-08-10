"""
Builds the prompt sent to the Vision LLM at runtime from rules.json.

The rules file is not the prompt -- this module assembles a fixed system
instruction, the subset of rules that require visual judgement (excluding
purely backend rules like IMAGE_SPECIFICATIONS), and the required JSON
response schema, into a single prompt string. Rules can change without
touching this code.
"""

import json

from config import RULES_PATH, SAFE_ZONE_MARGIN_PERCENT

SYSTEM_INSTRUCTION = """You are a design compliance reviewer for a streaming platform's in-app \
thumbnails and banners. You evaluate ONLY the rules provided to you below. Do not invent \
additional rules, standards, or opinions beyond what is listed. Every judgement you make must be \
grounded in something observable in the image -- cite what you actually see (position, contrast, \
overlap, text content, element count) in your "reason" and "evidence" fields, not generic advice.

You are NOT responsible for measuring pixel dimensions or aspect ratios -- that is handled by a \
separate deterministic system. Do not comment on absolute pixel size.

For every rule, return status as exactly one of "PASS", "WARNING", or "FAIL", and confidence as a \
float between 0.0 and 1.0 reflecting how certain you are given what is visible in the image."""

SAFE_ZONE_INSTRUCTION = f"""For the SAFE_ZONE rule specifically, you must also detect the bounding \
box of every critical element you can find: the primary subject, any faces, the main title text, \
the brand logo, and any sponsor logo. Return each detected box in the "detected_elements" object \
using the key names "primary_subject", "faces" (a list), "title", "brand_logo", and "sponsor_logo". \
Each box must be [ymin, xmin, ymax, xmax] normalized to a 0-1000 scale relative to the full image \
(top-left origin), matching standard Gemini object detection output. Omit a key entirely if that \
element is not present in the image -- do not guess coordinates for something you cannot see. \
A backend process will independently calculate whether these boxes fall within a {SAFE_ZONE_MARGIN_PERCENT}% \
safe margin from every edge, so your own SAFE_ZONE status/reason should reflect your best visual \
judgement, but the bounding boxes are what actually get used for the final determination."""

RESPONSE_FORMAT_INSTRUCTION = """Respond with a single JSON object with exactly two top-level keys:

"detected_elements": an object as described above for the SAFE_ZONE rule.

"rules": an object keyed by rule id (exactly as given below), where each value is an object with \
keys: "status", "confidence", "reason", "evidence" (a list of short strings describing what you \
observed), and "recommendation" (a short actionable suggestion, or null if status is PASS).

Return JSON only. No markdown formatting, no code fences, no commentary outside the JSON object."""


def _load_rules() -> list:
    with open(RULES_PATH, "r") as f:
        data = json.load(f)
    return data["rules"]


def get_vision_rules() -> list:
    """Rules the Vision AI is responsible for (everything except pure backend rules)."""
    return [r for r in _load_rules() if r["evaluation_type"] in ("vision", "vision+backend")]


def build_prompt() -> str:
    vision_rules = get_vision_rules()

    rules_block = json.dumps(
        [
            {
                "id": r["id"],
                "title": r["title"],
                "category": r["category"],
                "severity": r["severity"],
                "question": r["question"],
                "evaluation_instructions": r["evaluation_instructions"],
            }
            for r in vision_rules
        ],
        indent=2,
    )

    return "\n\n".join(
        [
            SYSTEM_INSTRUCTION,
            SAFE_ZONE_INSTRUCTION,
            "Here are the rules to evaluate, in the company's design guidelines:",
            rules_block,
            RESPONSE_FORMAT_INSTRUCTION,
        ]
    )
