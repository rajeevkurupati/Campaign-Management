# AI-Powered Campaign Management Platform

An AI-powered campaign management tool for career engagement platforms focused on women professionals. The platform lets marketing teams create, manage, and analyse campaigns using plain-English briefs that are automatically structured by an LLM — with built-in content compliance guardrails, plan-tier access control, and a RAG-backed brand knowledge base.

> **Disclaimer:** This is an independent prototype built for learning and demonstration purposes. The campaign types, audience segments, workflow design, and domain context used in this project were inspired by publicly available information from the [HerKey](https://www.herkey.com) platform (India's career engagement platform for women professionals). No proprietary data, internal systems, APIs, or confidential material belonging to HerKey or its parent organisation has been used. All code, architecture, and implementation are original work.

---

## Use Cases

| Who | What they do |
|---|---|
| **Marketing Manager** | Describe a campaign in plain English → AI extracts all structured fields → compliance check → launch in minutes |
| **Campaign Analyst** | View performance metrics, reach, CTR, conversions, and audience breakdown per campaign |
| **Content Team** | Use AI-suggested headlines and body copy as a starting point, then edit before publishing |
| **Operations Team** | Pause, resume, or end live campaigns; duplicate past campaigns as drafts |
| **Platform Admin** | Control what each customer tier can create via plan limits; enforce brand safety via AI compliance gate |

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

All fields are editable before publishing. The campaign then passes through an AI compliance gate before it can go live.

---

## Features

### Authentication
- **JWT-based auth** — register, login, token refresh via `/auth/register`, `/auth/login`, `/auth/me`
- **Per-user campaign scope** — each user sees their own campaigns + shared demo campaigns
- **Secure passwords** — bcrypt hashing (direct, not passlib)
- **Frontend auth overlay** — login/register modal with tab switching; JWT stored in `sessionStorage`

### Plan-Tier Guardrails
Platform operators control what each customer tier can create. Enforced server-side on every `POST /api/campaigns` call and available as a dry-run via `POST /api/campaigns/check-limits`.

| Limit | Starter | Growth | Enterprise |
|---|---|---|---|
| Active campaigns | 2 | 10 | Unlimited |
| Budget cap (per campaign) | ₹25,000 | ₹2,00,000 | Unlimited |
| Max campaign duration | 30 days | 60 days | Unlimited |
| Campaign types | Awareness, Event Drive | + Hiring Drive, Mentorship | All |
| Channels | Feed Posts, Email, Social Media | + Push, Groups, In-App | All |
| Audience segments | Job Seekers, Freshers, Career Break | + Women in Tech, Mid-Senior, Returnees | All |

Restricted options are visually locked in the wizard with a 🔒 indicator. Violations return a structured `403` with a human-readable message.

### AI Content Compliance (RAG-backed)
Every campaign brief passes through an AI compliance gate before it can be published:

1. **Retrieve** — the 3 most relevant brand policy chunks are fetched from the vector store using cosine similarity on the campaign content
2. **Assess** — the LLM scores the content 0–100 against platform guidelines (relevance, empowerment language, non-discrimination, truthfulness, clarity) — grounded in the retrieved policy text
3. **Gate** — score ≥ 80 with no issues = **PASS**; anything else = **BLOCK** with specific, actionable feedback

The validator runs automatically after AI extraction in the wizard. Campaigns cannot progress to publishing until they pass.

### RAG Knowledge Base
- **Drop-in document folder** — place any `.md` or `.txt` file in `backend/guidelines/` and it is automatically ingested at next startup
- **Change detection** — MD5 hash comparison; only changed files are re-embedded
- **Vector store** — ChromaDB `PersistentClient` with cosine similarity search
- **Embeddings** — OpenAI `text-embedding-3-small` if `OPENAI_API_KEY` is set; falls back to ChromaDB's local default (sentence-transformers `all-MiniLM-L6-v2`)
- **Included document** — `HerKey_Brand_Content_Guidelines.md` (715 lines): brand voice, campaign type definitions, prohibited content rules, audience segment profiles, ASCI / Indian employment law compliance, scoring rubric with borderline case examples

### Campaign Management
- **Campaign List** — filterable by status (Active / Scheduled / Draft / Ended / Paused), live counts
- **Campaign Detail Modal** — 4-tab deep-dive: Overview (KPI tiles, reach bar chart, channel breakdown), Reach & Impressions, Audience segments, Engagement funnel
- **AI-First Wizard** — 5-step campaign creation:
  1. Plain-English brief → AI extraction → editable result card → compliance check
  2. Visual asset (style picker + AI mock generator / image upload)
  3. Audience segments & location targeting (plan-locked options shown)
  4. Distribution channels & budget (plan-locked options shown, budget cap hint)
  5. Preview & publish
- **Status Actions** — Pause, Resume, Launch Now, End, Duplicate
- **Demo campaigns** — 5 pre-seeded campaigns (user_id = NULL) visible to all users; cannot be modified

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Browser (file://)                          │
│                                                                  │
│  index.html — Vanilla JS + CSS                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Auth Overlay  │  Campaign List  │  Wizard (5-step)          │ │
│  │  Plan Locks    │  Detail Modal   │  Compliance Panel         │ │
│  └─────────────────────────────────────────────────────────────┘ │
│       │ Bearer token (JWT)          │ apiFetch() wrapper         │
└───────┼─────────────────────────────┼──────────────────────────-─┘
        │                             │
        ▼                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                  FastAPI  (localhost:8000)                        │
│                                                                  │
│  /auth/*                 JWT register / login / me               │
│  /api/campaigns          CRUD (auth-gated, plan-enforced)        │
│  /api/campaigns/extract  AI brief → structured fields            │
│  /api/campaigns/validate AI compliance check (RAG-backed)        │
│  /api/campaigns/check-limits  Dry-run plan limit check           │
│                                                                  │
│  ┌──────────────┐  ┌───────────────────┐  ┌──────────────────┐  │
│  │  SQLite DB   │  │  LLM Agents       │  │  RAG Engine      │  │
│  │  campaigns   │  │  extractor.py     │  │  ChromaDB        │  │
│  │  users       │  │  content_         │  │  ingestion.py    │  │
│  │  SQLModel    │  │  validator.py     │  │  retriever.py    │  │
│  └──────────────┘  │  Anthropic/OpenAI │  └──────────────────┘  │
│                    └───────────────────┘         ▲              │
│                                                  │              │
│  ┌───────────────────────────────────────────────┘              │
│  │  backend/guidelines/*.md  (brand policy documents)           │
│  └──────────────────────────────────────────────────────────────┘
└──────────────────────────────────────────────────────────────────┘
```

### Key design decisions
- **Single HTML file** — the entire frontend is `index.html` (no build step, no npm)
- **Provider-agnostic LLM** — `agents/extractor.py` and `agents/content_validator.py` are provider factories; switching requires only a `.env` change
- **RAG fail-safe** — `retriever.py` catches all exceptions and returns `''`; the validator works identically without RAG
- **Plan limits enforced twice** — frontend locks the UI for UX; backend re-checks on every write for security
- **Demo campaigns via NULL user_id** — seeded campaigns have `user_id = NULL`, making them visible to all authenticated users but unmodifiable

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JavaScript (no framework) |
| Backend | Python 3.10+, FastAPI, Uvicorn |
| Database | SQLite via SQLModel (SQLAlchemy + Pydantic) |
| Auth | JWT (python-jose), bcrypt |
| AI — Anthropic | `anthropic` SDK, Claude 3.5 Haiku, tool_use + prompt caching |
| AI — OpenAI | `openai` SDK, GPT-4o Mini, function calling |
| RAG / Vector DB | ChromaDB (PersistentClient), OpenAI `text-embedding-3-small` |
| Validation | Pydantic v2 |

---

## Project Structure

```
Campaign-Management/
├── index.html                        # Entire frontend (UI, styles, JS, auth, plan locks)
├── README.md
└── backend/
    ├── main.py                       # FastAPI app, startup (RAG ingest + DB migrate + seed)
    ├── config.py                     # .env reader + validation
    ├── database.py                   # SQLite engine + session factory
    ├── requirements.txt
    ├── .env.example                  # Template — copy to .env and fill keys
    ├── test_api.py                   # Integration test suite (runs in-process)
    │
    ├── auth/                         # JWT authentication
    │   ├── models.py                 # User table + UserCreate / UserRead / Token schemas
    │   ├── utils.py                  # hash_password, verify_password, create/decode JWT
    │   ├── dependencies.py           # get_current_user FastAPI dependency
    │   └── router.py                 # /auth/register  /auth/login  /auth/me
    │
    ├── plans/
    │   └── __init__.py               # PLANS dict (Starter/Growth/Enterprise limits) + get_plan()
    │
    ├── models/
    │   ├── campaign.py               # Pydantic schemas for AI extraction
    │   ├── db_models.py              # SQLModel Campaign table (incl. user_id FK)
    │   └── guardrails.py             # LimitCheckRequest/Result, ValidateRequest/Result schemas
    │
    ├── agents/
    │   ├── extractor.py              # AI brief → structured campaign fields
    │   └── content_validator.py      # AI compliance check (RAG-augmented)
    │
    ├── routers/
    │   ├── campaigns.py              # Campaign CRUD (auth-gated, plan-enforced)
    │   └── guardrails.py             # /validate  /check-limits
    │
    ├── rag/
    │   ├── ingestion.py              # Chunk + embed guidelines docs → ChromaDB
    │   └── retriever.py              # Cosine similarity search → prompt-ready chunks
    │
    └── guidelines/                   # Drop .md or .txt files here — auto-ingested at startup
        └── HerKey_Brand_Content_Guidelines.md
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

Edit `.env` and fill in your keys:
```env
# Choose provider: anthropic | openai
LLM_PROVIDER=openai

ANTHROPIC_API_KEY=your-anthropic-api-key-here
ANTHROPIC_MODEL=claude-3-5-haiku-20241022

OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini

# JWT — change this to a long random string in production
# Generate one: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=change-this-to-a-random-secret-in-production
JWT_EXPIRE_MINUTES=1440
```

### 3. Install dependencies & start the backend
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

On first run the server will:
1. Ingest `backend/guidelines/*.md` into the ChromaDB vector store
2. Create the SQLite database
3. Run schema migrations (adds `user_id` column to existing databases)
4. Seed 5 demo campaigns with realistic metrics

Verify it's running: http://localhost:8000  
Interactive API docs: http://localhost:8000/docs

### 4. Open the frontend
Open `index.html` directly in your browser — no web server needed:
```
File → Open → Campaign-Management/index.html
```
An auth overlay will appear. Register a new account (plan defaults to `starter`) to log in.

### 5. Run the integration tests
```bash
# From backend/ directory
python test_api.py
```
Tests cover: health check, auth (register/login/wrong-password/me), campaign CRUD, all plan limit violations (count, budget, type, segment, duration), and the check-limits dry-run endpoint.

---

## API Reference

All `/api/*` endpoints require `Authorization: Bearer <token>`. Obtain a token via `POST /auth/login`.

### Auth

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | — | Create account → returns JWT + user |
| `POST` | `/auth/login` | — | Login → returns JWT + user |
| `GET` | `/auth/me` | ✓ | Current user info |

### Campaigns

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/campaigns` | ✓ | List own + demo campaigns (newest first) |
| `POST` | `/api/campaigns` | ✓ | Create campaign (plan limits enforced) |
| `GET` | `/api/campaigns/{id}` | ✓ | Get single campaign |
| `PATCH` | `/api/campaigns/{id}` | ✓ | Partial update (own campaigns only) |
| `DELETE` | `/api/campaigns/{id}` | ✓ | Delete (own campaigns only) |
| `POST` | `/api/campaigns/extract` | ✓ | AI brief → structured campaign fields |
| `POST` | `/api/campaigns/validate` | ✓ | AI compliance check (RAG-backed) |
| `POST` | `/api/campaigns/check-limits` | ✓ | Dry-run plan limit check |

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Status + active LLM provider |

### Key endpoint examples

**Register**
```json
POST /auth/register
{ "name": "Ada Lovelace", "email": "ada@example.com", "password": "secret123", "plan": "starter" }

→ 201
{ "access_token": "eyJ...", "token_type": "bearer", "user": { "id": 1, "name": "Ada Lovelace", "plan": "starter" } }
```

**Check plan limits (dry-run)**
```json
POST /api/campaigns/check-limits
{ "campaign_type": "Hiring Drive", "budget": 50000, "audience_segments": ["Entrepreneurs"] }

→ 200
{
  "ok": false,
  "plan": "Starter",
  "violations": [
    { "field": "campaign_type", "message": "Campaign type 'Hiring Drive' is not available on the Starter plan. Available types: Awareness, Event Drive." },
    { "field": "budget",        "message": "Budget ₹50,000 exceeds the Starter plan cap of ₹25,000." },
    { "field": "audience_segments", "message": "Segment(s) not available on your Starter plan: Entrepreneurs." }
  ]
}
```

**Validate content (RAG-backed)**
```json
POST /api/campaigns/validate
{
  "brief": "Awareness campaign for women returning from career breaks.",
  "headline": "Your Career Break Ends Here",
  "body_copy": "A 6-week bootcamp with mentorship and placement support.",
  "campaign_type": "Awareness"
}

→ 200
{
  "ok": true,
  "score": 91,
  "gate": "pass",
  "summary": "Campaign is career-relevant, empowering, and fully compliant with platform guidelines.",
  "issues": [],
  "usage": { "provider": "openai", "model": "gpt-4o-mini", "input_tokens": 1240, "output_tokens": 95 }
}
```

---

## Adding Guidelines Documents

Drop any `.md` or `.txt` file into `backend/guidelines/` and restart the server. The RAG engine will:
1. Detect the new file (MD5 hash comparison)
2. Chunk it by paragraph (800-char chunks, 100-char overlap)
3. Embed it with OpenAI `text-embedding-3-small` (or local fallback)
4. Store it in `backend/chroma_db/` (gitignored)

The content validator will immediately start citing the new document when assessing relevant campaigns.

---

## Switching LLM Providers

No code changes needed — just update `.env` and restart:

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key-here
```

Both the extractor and the content validator use the same provider. Embeddings always use OpenAI `text-embedding-3-small` if `OPENAI_API_KEY` is set, regardless of `LLM_PROVIDER`.

---

## Roadmap

- [x] ~~Auth — user login, campaigns scoped per user/organisation~~
- [x] ~~Plan-tier guardrails — operator-controlled limits per customer tier~~
- [x] ~~AI content compliance gate — brand safety + relevance scoring~~
- [x] ~~RAG knowledge base — ChromaDB + drop-in guidelines folder~~
- [ ] Edit campaign — re-open wizard pre-filled with existing campaign data
- [ ] Approval workflow — campaigns require operator sign-off before going live
- [ ] Real image generation — integrate DALL-E 3 or Stable Diffusion for campaign visuals
- [ ] Real analytics — replace simulated metrics with actual event tracking
- [ ] Export — download campaign performance as PDF or CSV
- [ ] Multi-tenant — campaigns scoped per organisation, not just per user
