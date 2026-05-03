"""
Shared system prompt and tool definition used by all extraction agents.
Centralised here so Anthropic and OpenAI agents stay in sync.
"""

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert campaign strategist for HerKey, India's \
largest career engagement platform for women professionals.

Your job is to analyse a campaign brief written in plain English and extract \
structured campaign details using the extract_campaign_details tool.

## HerKey platform context
HerKey serves women across all career stages:
- Freshers & early-career women
- Mid-senior professionals (3–15 years)
- Senior leaders & C-suite aspirants
- Career-break returnees
- Women entrepreneurs & founders
- Women in tech, data, product, engineering

## Campaign types
- Hiring Drive  → brand/employer hiring campaigns, job fairs, recruit drives
- Awareness     → brand visibility, returnee programs, community building
- Event Drive   → summits, webinars, workshops, conferences, bootcamps
- Learning      → courses, upskilling, certifications, training programs
- Mentorship    → mentor-matching, leadership cohorts, coaching programs
- Custom        → anything that doesn't fit the above

## Extraction rules
1. Infer campaign_type from context clues (recruit/hiring → Hiring Drive, \
event/summit → Event Drive, learn/upskill → Learning, mentor/cohort → \
Mentorship, awareness/return → Awareness).
2. Match tone to the brief's language and audience:
   - Formal, corporate, executive language → "Professional & Aspirational"
   - Community-focused, inclusive, return-to-work → "Warm & Inclusive"
   - Festive, energetic, celebratory → "Bold & Celebratory"
   - Technology, engineering, digital → "Tech-Forward"
3. Write headline: compelling, ≤10 words, resonates with Indian women \
professionals, present-tense or imperative.
4. Write body_copy: 2–3 sentences, warm and empowering, action-oriented, \
HerKey brand voice.
5. Dates:
   - If a specific month/date is mentioned, use it.
   - If "end of May" → 2026-05-31, "June" → 2026-06-30, etc.
   - If no start date mentioned, default to 2026-05-10.
   - If no end date mentioned, default to 30 days after start.
   - All dates must be in 2026 unless otherwise stated.
6. target_number: extract any mentioned number (500 applications, 2000 \
registrations). If none mentioned, use a sensible default per campaign type \
(Hiring Drive: 500, Event Drive: 1000, Learning: 2000, Mentorship: 200, \
Awareness: 10000).
7. audience_segments: pick all that apply from the allowed list based on \
context clues. Always include at least one.
8. locations: pick all mentioned. If none mentioned, use ["All India"]."""


# ── Tool / function definition (provider-agnostic schema) ────────────────────
# The same JSON schema is used for both Anthropic tool_use and OpenAI
# function-calling — only the wrapper format differs in each agent file.
TOOL_SCHEMA = {
    "name": "extract_campaign_details",
    "description": (
        "Extract structured campaign details from a plain-English brief. "
        "Call this tool once with all fields populated."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "campaign_type": {
                "type": "string",
                "enum": [
                    "Awareness", "Event Drive", "Hiring Drive",
                    "Learning", "Mentorship", "Custom",
                ],
                "description": "Primary campaign category",
            },
            "tone": {
                "type": "string",
                "enum": [
                    "Professional & Aspirational",
                    "Warm & Inclusive",
                    "Bold & Celebratory",
                    "Tech-Forward",
                ],
                "description": "Communication tone and style",
            },
            "headline": {
                "type": "string",
                "description": "Short, punchy campaign headline (≤10 words)",
            },
            "body_copy": {
                "type": "string",
                "description": "2–3 sentence campaign description in HerKey brand voice",
            },
            "objective": {
                "type": "string",
                "enum": [
                    "Job Applications",
                    "Registrations",
                    "Session Attendance",
                    "Community Growth",
                    "Profile Views",
                ],
                "description": "Primary conversion goal",
            },
            "target_number": {
                "type": "integer",
                "description": "Numeric goal (e.g. 500 applications, 2000 registrations)",
                "minimum": 1,
            },
            "start_date": {
                "type": "string",
                "description": "Campaign start date in YYYY-MM-DD format",
                "pattern": r"^\d{4}-\d{2}-\d{2}$",
            },
            "end_date": {
                "type": "string",
                "description": "Campaign end date in YYYY-MM-DD format",
                "pattern": r"^\d{4}-\d{2}-\d{2}$",
            },
            "audience_segments": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "Job Seekers", "Career Break", "Women in Tech",
                        "Mid-Senior", "Freshers", "Returnees", "Entrepreneurs",
                    ],
                },
                "description": "Target audience segments (pick all that apply)",
                "minItems": 1,
            },
            "locations": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "Bengaluru", "Mumbai", "Delhi NCR",
                        "Hyderabad", "Pune", "All India",
                    ],
                },
                "description": "Target locations (use ['All India'] if none specified)",
                "minItems": 1,
            },
        },
        "required": [
            "campaign_type", "tone", "headline", "body_copy",
            "objective", "target_number", "start_date", "end_date",
            "audience_segments", "locations",
        ],
    },
}

# ── Anthropic-formatted tool (wraps schema under "input_schema") ──────────────
EXTRACT_TOOL = {
    "name": TOOL_SCHEMA["name"],
    "description": TOOL_SCHEMA["description"],
    "input_schema": TOOL_SCHEMA["parameters"],
}

# ── OpenAI-formatted function (wraps schema under "function") ─────────────────
OPENAI_FUNCTION = {
    "type": "function",
    "function": {
        "name": TOOL_SCHEMA["name"],
        "description": TOOL_SCHEMA["description"],
        "parameters": TOOL_SCHEMA["parameters"],
    },
}
