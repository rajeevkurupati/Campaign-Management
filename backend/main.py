"""
HerKey Campaign API — Phase 2
==============================
Run:
    pip install -r requirements.txt
    cp .env.example .env          # fill in your API key(s)
    uvicorn main:app --reload --port 8000

Supported providers (set LLM_PROVIDER in .env):
    anthropic   — Claude via Anthropic API  (default)
    openai      — GPT via OpenAI API
"""

import config  # validates .env on import

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models.campaign import ExtractRequest, ExtractResponse
from agents.extractor import extract_campaign

# ── Validate config on startup ────────────────────────────────────────────────
try:
    config.validate()
except ValueError as exc:
    raise SystemExit(f"[HerKey] Config error: {exc}") from exc

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="HerKey Campaign API",
    description="AI-powered campaign management backend",
    version="0.2.0",
)

# Allow the static frontend (served on :3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "HerKey Campaign API",
        "version": app.version,
        "provider": config.LLM_PROVIDER,
        "docs": "/docs",
        "health": "/health",
        "extract": "POST /api/campaigns/extract",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": app.version,
        "provider": config.LLM_PROVIDER,
    }


@app.post("/api/campaigns/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest):
    """
    Brief Extraction Agent
    ----------------------
    Accepts a plain-English campaign brief and returns structured campaign
    details extracted by the configured LLM provider.

    Example request body:
        {
            "brief": "Hiring drive for women in tech at top 25 companies.
                      Target 500 job applications by May 31 2026."
        }
    """
    result = extract_campaign(req.brief)

    if not result.ok:
        raise HTTPException(status_code=422, detail=result.error)

    return result
