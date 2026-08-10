"""
Thin wrapper around the Gemini 2.5 Flash Vision API.

Sends the uploaded thumbnail plus the dynamically built prompt, and asks
Gemini to return JSON matching the schema described in prompt_builder.py.
This module knows nothing about design rules -- it just calls the model
and hands back parsed JSON (or raises).
"""

import io
import json

from fastapi import HTTPException
from google import genai
from google.genai import types
from PIL import Image

from config import GEMINI_API_KEY, GEMINI_MODEL

_client = None


def _get_client() -> genai.Client:
    global _client
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not configured on the server. Set it in backend/.env.",
        )
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _image_to_bytes(image: Image.Image, mime_type: str) -> bytes:
    buf = io.BytesIO()
    fmt = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}.get(mime_type, "PNG")
    # Convert palette/CMYK modes that some formats choke on when re-encoded.
    save_image = image.convert("RGB") if fmt == "JPEG" and image.mode not in ("RGB", "L") else image
    save_image.save(buf, format=fmt)
    return buf.getvalue()


def evaluate_with_vision_ai(image: Image.Image, mime_type: str, prompt: str) -> dict:
    """
    Calls Gemini with the image + prompt, requests JSON output, and returns
    the parsed dict. Raises HTTPException on any failure so the API layer
    can surface a clean error instead of a stack trace.
    """
    client = _get_client()
    image_bytes = _image_to_bytes(image, mime_type)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vision AI request failed: {exc}")

    raw_text = (response.text or "").strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="Vision AI returned a response that could not be parsed as JSON.",
        )
