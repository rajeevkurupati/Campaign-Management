# AI-Powered Campaign Management Platform

An AI-powered campaign management tool for career engagement platforms focused on women professionals. The platform lets marketing teams create, manage, and analyse campaigns using plain-English briefs that are automatically structured by an LLM.

> **Disclaimer:** This is an independent prototype built for learning and demonstration purposes. The campaign types, audience segments, workflow design, and domain context used in this project were inspired by publicly available information from the [HerKey](https://www.herkey.com) platform (India's career engagement platform for women professionals). No proprietary data, internal systems, APIs, or confidential material belonging to HerKey or its parent organisation has been used. All code, architecture, and implementation are original work.

---

## Use Cases

| Who | What they do |
|---|---|
| **Marketing Manager** | Describe a campaign in plain English → AI extracts all structured fields → review and launch in minutes |
| **Campaign Analyst** | View performance metrics, reach, CTR, conversions, and audience breakdown per campaign |
| **Content Team** | Use AI-suggested headlines and body copy as a starting point, then edit before publishing |
| **Operations Team** | Pause, resume, or end live campaigns; duplicate past campaigns as drafts |

### Example brief → structured campaign
> *"Run a hiring drive for women in tech across Bengaluru, Mumbai and Delhi NCR. Partner with top 25 employers. Target 1,000 job applications by end of July."*

The AI extracts:
- **Type** → Hiring Drive
- **Tone** → Professional & Aspirational
- **Headline** → *25 Top Employers. 1,000 Opportunities.*
- **Objective** → Job Applications · Target: 1,000
- **Dates** → 10 May – 31 Jul 2026
- **Audience** → Job Seekers, Women in Tech, Mid-Senior
- **Locations** → Bengaluru, Mumbai, Delhi NCR

All fields are editable before publishing.

---

## Features

### Frontend
- **Campaign List** — filterable by status (Active / Scheduled / Draft / Ended), live counts
- **Campaign Detail Modal** — 4-tab deep-dive per campaign:
  - *Overview* — KPI tiles, daily reach bar chart, channel breakdown, milestones
  - *Reach & Impressions* — unique viewers, avg. frequency, channel performance
  - *Audience* — segment breakdown, location heatmap
  - *Engagement* — CTR, saves, conversion funnel
- **AI-First Wizard** — 5-step campaign creation:
  1. Plain-English brief → AI extraction → editable result card
  2. Visual asset (style picker + AI mock generator / image upload)
  3. Audience segments & location targeting
  4. Distribution channels & budget
  5. Preview & publish
- **Status Actions** — Pause, Resume, Launch Now, End, Duplicate
- **Offline Fallback** — works without backend using mock AI extraction and local DOM

### Backend
- **AI Brief Extraction** — `POST /api/campaigns/extract` — LLM parses a brief into structured JSON using tool/function calling
- **Campaign CRUD** — `GET / POST / PATCH / DELETE /api/campaigns`
- **SQLite Persistence** — campaigns survive page refreshes; 5 demo campaigns seeded on first run
- **Multi-provider LLM** — switch between Anthropic (Claude) and OpenAI (GPT) via a single `.env` variable
- **Prompt Caching** — Anthropic's `cache_control: ephemeral` keeps the system prompt cached for 5 minutes, reducing cost on repeated extractions

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (file://)                    │
│                                                         │
│   index.html  ──  Vanilla JS + CSS                      │
│   ┌──────────────────────────────────────────────────┐  │
│   │  Campaign List  │  Detail Modal  │  Wizard (5-step)│ │
│   └──────────────────────────────────────────────────┘  │
│             │  fetch()                  │ fetch()        │
└─────────────┼──────────────────────────┼────────────────┘
              │                          │
              ▼                          ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI  (localhost:8000)                   │
│                                                         │
│   GET/POST/PATCH/DELETE  /api/campaigns                 │
│   POST                   /api/campaigns/extract         │
│                                                         │
│   ┌─────────────┐    ┌──────────────────────────────┐  │
│   │  SQLite DB  │    │   LLM Agent (tool calling)    │  │
│   │  campaigns  │    │                              │  │
│   │  SQLModel   │    │  Anthropic (Claude tool_use) │  │
│   └─────────────┘    │  OpenAI    (function calling)│  │
│                      └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Key design decisions
- **Single HTML file** — the entire frontend is `index.html` (no build step, no npm)
- **Provider-agnostic extraction** — `agents/extractor.py` is a factory; adding a new LLM provider requires only one new file
- **Shared tool schema** — `agents/_prompt.py` holds the system prompt and JSON schema once; both Anthropic and OpenAI agents import from it
- **Offline-first frontend** — all API calls have fallbacks so the UI works without the backend running

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JavaScript (no framework) |
| Backend | Python 3.10+, FastAPI, Uvicorn |
| Database | SQLite via SQLModel (SQLAlchemy + Pydantic) |
| AI — Anthropic | `anthropic` SDK, Claude 3.5 Haiku, tool_use + prompt caching |
| AI — OpenAI | `openai` SDK, GPT-4o Mini, function calling |
| Validation | Pydantic v2 |

---

## Project Structure

```
Campaign-Management/
├── index.html                  # Entire frontend (UI, styles, JS)
├── backend/
│   ├── main.py                 # FastAPI app, startup, routing
│   ├── config.py               # .env reader + validation
│   ├── database.py             # SQLite engine + session factory
│   ├── requirements.txt
│   ├── .env.example            # Template — copy to .env and fill keys
│   ├── models/
│   │   ├── campaign.py         # Pydantic schemas for AI extraction
│   │   └── db_models.py        # SQLModel table + CRUD schemas
│   ├── agents/
│   │   ├── _prompt.py          # Shared system prompt + tool schema
│   │   ├── extractor.py        # Provider factory (routes to Anthropic/OpenAI)
│   │   ├── anthropic_extractor.py
│   │   └── openai_extractor.py
│   └── routers/
│       └── campaigns.py        # Campaign CRUD endpoints
└── README.md
```

---

## Setup & Usage

### Prerequisites
- Python 3.10 or higher
- An API key for Anthropic **or** OpenAI (or both)

### 1. Clone the repo
```bash
git clone https://github.com/rajeevkurupati/Campaign-Management.git
cd Campaign-Management
```

### 2. Configure the backend
```bash
cd backend
cp .env.example .env
```

Edit `.env` and fill in your key:
```env
# Choose provider: anthropic | openai
LLM_PROVIDER=anthropic

ANTHROPIC_API_KEY=your-anthropic-api-key-here
ANTHROPIC_MODEL=claude-3-5-haiku-20241022

# Only needed if LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
```

### 3. Install dependencies & start the backend
```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

On first run the server will:
- Create the SQLite database file
- Seed 5 demo campaigns with realistic metrics

Verify it's running: http://localhost:8000

Interactive API docs: http://localhost:8000/docs

### 4. Open the frontend
Open `index.html` directly in your browser (no web server needed):
```
File → Open → Campaign-Management/index.html
```
Then click **Campaigns** in the left sidebar.

> **Note:** If the backend is offline, the frontend still works using mock AI extraction and local-only campaign cards (not persisted across refreshes).

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/campaigns` | List all campaigns (newest first) |
| `POST` | `/api/campaigns` | Create a new campaign |
| `GET` | `/api/campaigns/{id}` | Get a single campaign |
| `PATCH` | `/api/campaigns/{id}` | Update fields (status, metrics, etc.) |
| `DELETE` | `/api/campaigns/{id}` | Delete a campaign |
| `POST` | `/api/campaigns/extract` | AI brief → structured campaign fields |
| `GET` | `/health` | Health check + active provider |

### Extract endpoint example

**Request**
```json
POST /api/campaigns/extract
{
  "brief": "Run an awareness campaign for women returning from career breaks. 
            Focus on Tier 1 cities. Target 2,500 registrations by June 2026."
}
```

**Response**
```json
{
  "ok": true,
  "data": {
    "campaign_type": "Awareness",
    "tone": "Warm & Inclusive",
    "headline": "Your Career Break Ends Here",
    "body_copy": "A structured 6-week bootcamp with mentorship and live placement support...",
    "objective": "Registrations",
    "target_number": 2500,
    "start_date": "2026-05-10",
    "end_date": "2026-06-30",
    "audience_segments": ["Career Break", "Returnees"],
    "locations": ["Bengaluru", "Mumbai", "Delhi NCR"]
  },
  "usage": {
    "provider": "anthropic",
    "model": "claude-3-5-haiku-20241022",
    "input_tokens": 892,
    "output_tokens": 187,
    "cache_read_tokens": 756
  }
}
```

---

## Switching LLM Providers

No code changes needed — just update `.env` and restart:

```env
# Use OpenAI instead
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key-here
```

Both providers use the same tool/function schema defined in `agents/_prompt.py`.

---

## Roadmap

- [ ] Edit campaign — re-open wizard pre-filled with existing campaign data
- [ ] Real image generation — integrate DALL-E 3 or Stable Diffusion for campaign visuals
- [ ] Real analytics — replace simulated metrics with actual event tracking
- [ ] Auth — user login, campaigns scoped per user/organisation
- [ ] Export — download campaign performance as PDF or CSV
