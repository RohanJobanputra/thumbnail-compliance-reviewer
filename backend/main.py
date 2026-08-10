"""
FastAPI entry point.

Routes:
  GET  /api/asset-types  -> list of valid asset types (for the dropdown)
  POST /api/review       -> upload image + asset_type, get back a ComplianceReport

Static frontend files are mounted at "/" last, so /api/* is always matched
first -- this lets you run the whole app with a single `uvicorn` command
and no CORS configuration needed.
"""

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from models import ComplianceReport
from services import image_validator, prompt_builder, gemini_client, report_aggregator

app = FastAPI(title="Thumbnail Compliance Reviewer")

# Permissive CORS so the frontend can also be served separately (e.g. a
# quick `python -m http.server` during development) without extra setup.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/asset-types")
def get_asset_types():
    return {"asset_types": image_validator.get_asset_types()}


@app.post("/api/review", response_model=ComplianceReport)
async def review_thumbnail(
    file: UploadFile = File(...),
    asset_type: str = Form(...),
):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Step 1: deterministic backend validation. Raises early on unusable
    # input, before any AI call is made.
    image, technical_validation = image_validator.validate_upload(
        file_bytes=file_bytes,
        content_type=file.content_type,
        asset_type=asset_type,
    )

    # Step 2: build the prompt dynamically from rules.json.
    prompt = prompt_builder.build_prompt()

    # Step 3: send image + prompt to Gemini 2.5 Flash.
    ai_response = gemini_client.evaluate_with_vision_ai(
        image=image,
        mime_type=file.content_type,
        prompt=prompt,
    )

    # Step 4: merge backend + AI results into one unified report.
    report = report_aggregator.build_report(
        filename=file.filename,
        asset_type=asset_type,
        technical_validation=technical_validation,
        ai_response=ai_response,
    )

    return report


# Serve the frontend as static files. Must be mounted after the API routes
# above so it doesn't shadow them.
FRONTEND_DIR = Path(__file__).resolve().parent / "static"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
