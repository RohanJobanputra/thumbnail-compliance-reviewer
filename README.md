# Thumbnail Compliance Reviewer

An AI-powered tool for designers to check thumbnails/banners against a company's
design guidelines before they ship. Deterministic checks (dimensions, aspect
ratio) run entirely in the backend; subjective visual checks (subject
prominence, hierarchy, clutter, readability, branding, safe zone) are
evaluated by Gemini 2.5 Flash and merged into one report.

## How it works

1. You upload a thumbnail and pick an asset type.
2. The backend reads the image and checks its dimensions/aspect ratio against
   `backend/data/asset_specifications.json` — no AI call needed for this.
3. The backend builds a prompt at runtime from `backend/data/rules.json` and
   sends it, with the image, to Gemini 2.5 Flash.
4. Gemini returns structured JSON: a status/reason/evidence/recommendation
   for each visual rule, plus bounding boxes for the primary subject, faces,
   title, and logos.
5. The backend independently calculates the 7% safe-margin check from those
   bounding boxes (it doesn't just trust Gemini's own opinion on safe zone —
   it does the geometry itself).
6. Everything is merged into one compliance report and rendered in the
   frontend, with no distinction shown between backend-checked and
   AI-checked items.

## Project structure

```
backend/
  main.py                      FastAPI app + routes
  config.py                    env vars, paths, constants
  models.py                    Pydantic response models
  data/
    rules.json                 design guideline rules (drives the AI prompt)
    asset_specifications.json  expected width/height per asset type
  services/
    image_validator.py         deterministic dimension/aspect-ratio checks
    prompt_builder.py          builds the Gemini prompt from rules.json
    gemini_client.py           calls Gemini 2.5 Flash, parses JSON response
    safe_zone.py                7% margin math from bounding boxes
    report_aggregator.py       merges backend + AI results into one report
frontend/
  index.html / style.css / script.js   single-page upload + report UI
```

## Setup

**1. Get a Gemini API key**
Create one at https://aistudio.google.com/apikey if you don't have one yet.

**2. Install backend dependencies**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**3. Configure your API key**

```bash
cp .env.example .env
```

Then open `.env` and set:

```
GEMINI_API_KEY=your_actual_key_here
```

**4. Run it**

```bash
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** — the FastAPI server serves both the API
(`/api/*`) and the frontend directly, so there's nothing else to start.

## Adding or editing rules

Edit `backend/data/rules.json`. Any rule with `"evaluation_type": "vision"`
or `"vision+backend"` is automatically included in the next Gemini prompt —
no code changes needed. Rules with `"evaluation_type": "backend"` (currently
just `IMAGE_SPECIFICATIONS`) are handled entirely by
`services/image_validator.py` instead.

To add a new asset type, add an entry to `backend/data/asset_specifications.json`
— it will automatically appear in the frontend dropdown.

## Notes on the safe-zone implementation

The design guidelines describe safe-zone as an "approximate visual
assessment" for the MVP, since most vision APIs don't return object
coordinates. Gemini 2.5 Flash does support bounding-box detection, so this
build has the AI return bounding boxes for critical elements and does the
actual 7% margin math in the backend (`services/safe_zone.py`) — matching
what `rules.json` itself specifies for the SAFE_ZONE rule
(`"evaluation_type": "vision+backend"`). If Gemini can't detect any elements
in a given image, the code falls back to the AI's own qualitative
PASS/WARNING/FAIL judgement rather than failing the check outright.

## Known MVP limitations (matching the original scope)

- Single image upload only — no ZIP/batch support
- No authentication, no database, no persistence between requests
- No PSD support
- Only PNG/JPG/JPEG/WEBP accepted
