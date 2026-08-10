# Thumbnail Compliance Reviewer

An AI-powered tool that checks thumbnails/banners against a company's design guidelines.

## Tech Stack

* **Backend:** FastAPI + Python
* **Frontend:** HTML/CSS/JavaScript
* **AI:** Google Gemini API (`google-genai`)
* **Image processing:** Pillow

## Project Structure

```text
thumbnail-compliance-reviewer/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── requirements.txt
│   ├── data/
│   │   ├── rules.json
│   │   └── asset_specifications.json
│   └── services/
│       ├── gemini_client.py
│       ├── image_validator.py
│       ├── prompt_builder.py
│       ├── safe_zone.py
│       └── report_aggregator.py
└── frontend/
    ├── index.html
    ├── style.css
    └── script.js
```

## Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/RohanJobanputra/thumbnail-compliance-reviewer.git
cd thumbnail-compliance-reviewer
```

### 2. Create and activate a virtual environment

**Windows:**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add Gemini API key

Create a `.env` file inside `backend/`:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.6-flash
```

The API key can be created from Google AI Studio.

### 5. Start the application

From the `backend/` directory:

```bash
uvicorn main:app --reload --port 8000
```

Open:

```text
http://localhost:8000
```

The FastAPI server serves both the frontend and API.

## Changing Design Guidelines

The main guideline files are:

```text
backend/data/rules.json
backend/data/asset_specifications.json
```

### `rules.json`

Use this file to add, remove, or modify the **design/compliance rules** used by the application.

After changing the rules, restart the local server.

### `asset_specifications.json`

Use this file to add or modify **asset types and their required dimensions**.

Example:

```json
{
  "Vertical Thumbnail": {
    "width": 160,
    "height": 240
  }
}
```

New asset types added here will appear in the application's asset-type dropdown.

## Changing the Gemini API / Model

Gemini configuration is handled through environment variables:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.6-flash
```

To use a different Gemini model, change `GEMINI_MODEL` in `.env`.

To use a different API key, replace `GEMINI_API_KEY` with the new key.

**Do not commit `.env` or expose the API key in GitHub.**

For the deployed Render application, these values must be updated in the service's **Environment Variables** rather than in the repository.

## Deployment

The project is currently deployed on Render.

When changes are pushed to the `main` branch, Render can automatically redeploy the latest commit.

## Current MVP Limitations

* Single image upload
* No authentication
* No database/persistent storage
* No PSD support
* Supported formats: PNG, JPG, JPEG, WEBP
* Requires a valid Gemini API key
