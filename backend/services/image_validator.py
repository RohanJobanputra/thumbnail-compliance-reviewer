"""
All deterministic, mathematically-checkable validation lives here.

Per the design philosophy: anything measurable is handled entirely by the
backend and never delegated to the Vision AI. This module never calls out
to any AI -- it only reads image metadata with Pillow and compares it
against asset_specifications.json.
"""

import io
import json
from typing import Tuple
import pillow_avif  # noqa: F401 -- registers AVIF support with Pillow

from PIL import Image
from fastapi import HTTPException

from config import (
    ASSET_SPECS_PATH,
    ASPECT_RATIO_PASS_THRESHOLD,
    ASPECT_RATIO_WARNING_THRESHOLD,
    DIMENSION_PASS_THRESHOLD,
    DIMENSION_WARNING_THRESHOLD,
    SUPPORTED_MIME_TYPES,
)
from models import RuleResult, TechnicalValidation


def load_asset_specifications() -> dict:
    with open(ASSET_SPECS_PATH, "r") as f:
        return json.load(f)


def get_asset_types() -> list:
    return sorted(load_asset_specifications().keys())


def validate_upload(file_bytes: bytes, content_type: str, asset_type: str) -> Tuple[Image.Image, TechnicalValidation]:
    """
    Reads the uploaded image, validates its format/dimensions/aspect ratio
    against asset_specifications.json, and returns both the opened PIL
    image (needed downstream for the Vision AI call) and the technical
    validation result.

    Raises HTTPException for hard failures that should stop the pipeline
    before any AI call is made (unsupported format, corrupt file, or
    unknown asset type) -- there is no point spending an AI call on an
    image the backend already knows is unusable.
    """
    specs = load_asset_specifications()

    if asset_type not in specs:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown asset type '{asset_type}'. Valid options: {sorted(specs.keys())}",
        )

    if content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{content_type}'. Supported formats: PNG, JPG, JPEG, WEBP.",
        )

    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()
    except Exception:
        raise HTTPException(status_code=400, detail="The uploaded file could not be read as a valid image.")

    uploaded_width, uploaded_height = image.size
    expected = specs[asset_type]
    expected_width, expected_height = expected["width"], expected["height"]

    # Dimension check: this is a resolution-floor check, not a target
    # match. Aspect ratio is already validated separately above/below,
    # so once ratio is correct, a larger-than-target image is always
    # fine (it gets downscaled to fit) -- only a SMALLER-than-target
    # image is a real problem (upscaling introduces blur).
    width_scale = uploaded_width / expected_width
    height_scale = uploaded_height / expected_height
    min_scale = min(width_scale, height_scale)   # the more-constrained axis

    if min_scale >= 1.0:
        dim_status = "PASS"
        dim_recommendation = None
        dim_reason = (
            f"Uploaded image is {uploaded_width}x{uploaded_height}px, at or above the "
            f"required {expected_width}x{expected_height}px for '{asset_type}' "
            f"(scale: {min_scale:.2f}x). Will be downscaled to fit -- no quality loss."
        )
    elif min_scale >= (1 - DIMENSION_PASS_THRESHOLD):
        dim_status = "PASS"
        dim_recommendation = None
        dim_reason = (
            f"Uploaded image is {uploaded_width}x{uploaded_height}px, within "
            f"{(1-min_scale)*100:.1f}% of the required {expected_width}x{expected_height}px."
        )
    elif min_scale >= (1 - DIMENSION_WARNING_THRESHOLD):
        dim_status = "WARNING"
        dim_recommendation = (
            f"Image is {(1-min_scale)*100:.1f}% below the target resolution "
            f"({expected_width}x{expected_height}px) -- may look soft if upscaled."
        )
        dim_reason = (
            f"Uploaded image is {uploaded_width}x{uploaded_height}px, below the "
            f"required {expected_width}x{expected_height}px for '{asset_type}'."
        )
    else:
        dim_status = "FAIL"
        dim_recommendation = (
            f"Source a higher-resolution version -- at least {expected_width}x{expected_height}px "
            f"is required for '{asset_type}'."
        )
        dim_reason = (
            f"Uploaded image is {uploaded_width}x{uploaded_height}px, well below the "
            f"required {expected_width}x{expected_height}px for '{asset_type}' "
            f"(only {min_scale*100:.1f}% of target resolution)."
        )

    dimension_check = RuleResult(
        id="IMAGE_DIMENSIONS",
        title="Image Dimensions",
        category="Technical",
        severity="Critical",
        status=dim_status,
        confidence=1.0,
        reason=dim_reason,
        evidence=[
            f"uploaded={uploaded_width}x{uploaded_height}",
            f"expected={expected_width}x{expected_height}",
            f"scale={min_scale:.2f}x",
        ],
        recommendation=dim_recommendation,
        source="backend",
    )

    # Aspect ratio check: derived from the same dimensions, reported
    # separately because a resize tool might get the ratio right but the
    # absolute size wrong (or vice versa via cropping) -- these are two
    # different failure modes a designer needs to distinguish.
    
    uploaded_ratio = uploaded_width / uploaded_height
    expected_ratio = expected_width / expected_height

    # Relative percentage difference
    ratio_difference = abs(uploaded_ratio - expected_ratio) / expected_ratio

    if ratio_difference <= ASPECT_RATIO_PASS_THRESHOLD:
        status = "PASS"
        recommendation = None
    elif ratio_difference <= ASPECT_RATIO_WARNING_THRESHOLD:
        status = "WARNING"
        recommendation = (
            "Minor aspect ratio deviation detected. "
            "Consider recropping before publishing."
        )
    else:
        status = "FAIL"
        recommendation = (
            "Recrop or resize the image to match the required aspect ratio."
        )

    aspect_ratio_check = RuleResult(
    id="ASPECT_RATIO",
    title="Aspect Ratio",
    category="Technical",
    severity="Critical",
    status=status,
    confidence=1.0,
    reason=(
        f"Uploaded aspect ratio is {uploaded_ratio:.3f}; "
        f"expected is {expected_ratio:.3f}. "
        f"Difference: {ratio_difference*100:.1f}%."
    ),
    evidence=[
        f"uploaded_ratio={uploaded_ratio:.3f}",
        f"expected_ratio={expected_ratio:.3f}",
        f"difference={ratio_difference*100:.1f}%"
    ],
    recommendation=recommendation,
    source="backend",
)

    technical_validation = TechnicalValidation(
        uploaded_width=uploaded_width,
        uploaded_height=uploaded_height,
        expected_width=expected_width,
        expected_height=expected_height,
        asset_type=asset_type,
        dimension_check=dimension_check,
        aspect_ratio_check=aspect_ratio_check,
    )

    return image, technical_validation
