"""
Central configuration for the Thumbnail Compliance Reviewer backend.

Loads environment variables and exposes paths to the two data files that
drive the whole system: rules.json (what the Vision AI must evaluate) and
asset_specifications.json (what the backend validates deterministically).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

RULES_PATH = DATA_DIR / "rules.json"
ASSET_SPECS_PATH = DATA_DIR / "asset_specifications.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

print("KEY loaded:", bool(GEMINI_API_KEY))
print("KEY length:", len(GEMINI_API_KEY))
print("KEY prefix:", GEMINI_API_KEY[:8] if GEMINI_API_KEY else "EMPTY")
print("KEY suffix:", GEMINI_API_KEY[-4:] if GEMINI_API_KEY else "EMPTY")
print("MODEL repr:", repr(GEMINI_MODEL))

# Safe-zone margin from each edge, as specified in the design guidelines.
SAFE_ZONE_MARGIN_PERCENT = 7.0

# Formats the MVP accepts, per project scope.
SUPPORTED_IMAGE_FORMATS = {"PNG", "JPEG", "JPG", "WEBP"}
SUPPORTED_MIME_TYPES = {
    "image/png": "PNG",
    "image/jpeg": "JPEG",
    "image/webp": "WEBP",
}

# How much an image's aspect ratio may deviate from the spec's before it's
# flagged. Dimensions must match exactly to PASS; this only affects the
# aspect-ratio sub-check message when width/height are close but not exact.
# Relative aspect ratio thresholds
ASPECT_RATIO_PASS_THRESHOLD = 0.03      # ≤3%
ASPECT_RATIO_WARNING_THRESHOLD = 0.07   # >3% and ≤7%

# Relative dimension thresholds (uploaded width/height vs expected).
# Dimensions no longer require an exact pixel match -- both width and
# height are compared independently as % deviation, and the worse of
# the two decides the status.
DIMENSION_PASS_THRESHOLD = 0.03         # ≤3% deviation on both axes
DIMENSION_WARNING_THRESHOLD = 0.10      # >3% and ≤10%