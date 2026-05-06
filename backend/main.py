"""
Campaign Management API
========================
Run:
    pip install -r requirements.txt
    cp .env.example .env          # fill in your API key(s)
    uvicorn main:app --reload --port 8000

Supported LLM providers (set LLM_PROVIDER in .env):
    anthropic   — Claude via Anthropic API  (default)
    openai      — GPT via OpenAI API
"""

import config  # validates .env on import

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlmodel import Session, select

from database import create_db_and_tables, engine
from models.db_models import Campaign, CampaignCreate
from auth.router import router as auth_router
from routers.campaigns import router as campaigns_router
from routers.guardrails import router as guardrails_router

# ── Validate config on startup ────────────────────────────────────────────────
try:
    config.validate()
except ValueError as exc:
    raise SystemExit(f"[Campaign API] Config error: {exc}") from exc

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Campaign Management API",
    description="AI-powered campaign management backend with guardrails",
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5500", "http://127.0.0.1:5500",
        "null",   # file:// origin
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ───────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(guardrails_router)   # must come before campaigns_router (path ordering)
app.include_router(campaigns_router)


# ── Demo seed data ────────────────────────────────────────────────────────────
DEMO_CAMPAIGNS = [
    CampaignCreate(
        name="Women in Tech Summit 2026 – Registration Drive",
        campaign_type="Event Drive", status="active",
        tone="Tech-Forward",
        headline="Own the Stage at Women in Tech Summit 2026",
        body_copy="Drive registrations for the flagship Women in Tech Summit. Join 5,000+ women leaders, innovators, and changemakers for three days of inspiration.",
        objective="Registrations", target_number=5000,
        start_date="2026-04-10", end_date="2026-05-20",
        audience_segments="Women in Tech,Job Seekers,Mid-Senior",
        locations="Bengaluru,Mumbai,Delhi NCR",
        channels="Feed Posts,Email,Push Notifications",
        budget=48000,
    ),
    CampaignCreate(
        name="Return to Work Bootcamp – Spring 2026",
        campaign_type="Awareness", status="active",
        tone="Warm & Inclusive",
        headline="Your Career Break Ends Here",
        body_copy="Awareness & enrollment for women returning from a career break. A 6-week structured bootcamp with mentorship, skill refreshers, and live placement support.",
        objective="Registrations", target_number=2500,
        start_date="2026-04-25", end_date="2026-06-15",
        audience_segments="Career Break,Returnees,Freshers",
        locations="All India",
        channels="Feed Posts,Groups,Push Notifications",
        budget=32000,
    ),
    CampaignCreate(
        name="Hiring Drive Q2 2026 – Top 25 Employers",
        campaign_type="Hiring Drive", status="scheduled",
        tone="Professional & Aspirational",
        headline="25 Top Employers. 1,000 Opportunities.",
        body_copy="Partner-driven hiring campaign connecting ambitious women with India's top 25 employers across tech, finance, and consulting sectors.",
        objective="Job Applications", target_number=1000,
        start_date="2026-05-10", end_date="2026-07-31",
        audience_segments="Job Seekers,Women in Tech,Mid-Senior",
        locations="Bengaluru,Mumbai,Delhi NCR,Hyderabad,Pune",
        channels="Jobs Board,Email,Feed Posts",
        budget=75000,
    ),
    CampaignCreate(
        name="Leadership Mentorship Program – Cohort 4",
        campaign_type="Mentorship", status="draft",
        tone="Professional & Aspirational",
        headline="Lead. Mentor. Inspire. Join Cohort 4.",
        body_copy="Exclusive mentorship cohort pairing high-potential mid-senior women with C-suite leaders. Applications open soon.",
        objective="Registrations", target_number=200,
        audience_segments="Mid-Senior,Entrepreneurs,Women in Tech",
        locations="All India",
        channels="Email,Feed Posts,Groups",
        budget=None,
    ),
    CampaignCreate(
        name="New Year Career Reset 2026 – January Edition",
        campaign_type="Learning", status="ended",
        tone="Bold & Celebratory",
        headline="New Year, New Career — Reset & Rise",
        body_copy="January's flagship learning sprint. 31 days of daily career challenges, live workshops, and peer accountability groups for women across all career stages.",
        objective="Community Growth", target_number=10000,
        start_date="2026-01-01", end_date="2026-01-31",
        audience_segments="Job Seekers,Freshers,Career Break",
        locations="All India",
        channels="Feed Posts,Email,Push Notifications,WhatsApp",
        budget=52000,
    ),
]

DEMO_METRICS = [
    dict(reach=842310,  impressions=2100000, clicks=62480,  ctr="7.41%", conversions=4218,  progress_pct=84,  spent=31200),
    dict(reach=312000,  impressions=890000,  clicks=28400,  ctr="3.19%", conversions=1180,  progress_pct=47,  spent=18500),
    dict(reach=0,       impressions=0,       clicks=0,      ctr="0%",    conversions=0,     progress_pct=0,   spent=0),
    dict(reach=0,       impressions=0,       clicks=0,      ctr="0%",    conversions=0,     progress_pct=0,   spent=None),
    dict(reach=1840000, impressions=4200000, clicks=142000, ctr="7.72%", conversions=13420, progress_pct=134, spent=52000),
]


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    # 1. Create any new tables (User, etc.)
    create_db_and_tables()

    # 2. Migrate campaign table: add user_id column if it doesn't exist yet
    with engine.connect() as conn:
        existing_cols = [col["name"] for col in inspect(engine).get_columns("campaign")]
        if "user_id" not in existing_cols:
            conn.execute(text("ALTER TABLE campaign ADD COLUMN user_id INTEGER"))
            conn.commit()
            print("[Campaign API] Migration: added user_id column to campaign table")

    # 3. Seed demo campaigns (user_id = NULL so all users can see them)
    with Session(engine) as session:
        existing = session.exec(select(Campaign)).first()
        if existing:
            return
        for i, demo in enumerate(DEMO_CAMPAIGNS):
            c = Campaign.model_validate(demo)
            c.user_id = None   # explicitly mark as demo / unowned
            for key, val in DEMO_METRICS[i].items():
                setattr(c, key, val)
            session.add(c)
        session.commit()
        print("[Campaign API] Seeded 5 demo campaigns")


# ── Health / root routes ──────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name":     "Campaign Management API",
        "version":  app.version,
        "provider": config.LLM_PROVIDER,
        "docs":     "/docs",
        "health":   "/health",
    }


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version, "provider": config.LLM_PROVIDER}
