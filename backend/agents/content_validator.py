"""
AI content compliance validator.
Uses the same LLM provider as the extraction agent (set by LLM_PROVIDER in .env).

Checks campaign content against platform guidelines and returns a score,
gate (pass/block), and a list of specific issues.
"""
import json
from typing import Optional

import config
from models.guardrails import ValidationIssue, ValidationResult

# ── System prompt ─────────────────────────────────────────────────────────────

VALIDATOR_SYSTEM_PROMPT = """\
You are a content compliance reviewer for a career engagement platform for women professionals in India.

Your job: assess a campaign brief (and optionally headline / body copy) for compliance with the platform's guidelines, then call the validate_campaign_content tool with your verdict.

## Platform Guidelines

1. RELEVANCE — Campaigns must relate to career development, hiring, learning, networking, or professional growth specifically relevant to women professionals. A generic consumer goods ad, a personal loan ad, or a real estate campaign would score low.

2. NON-DISCRIMINATION — Content must not:
   - Restrict targeting by age, caste, religion, marital status, or pregnancy status
   - Use language that implies women are less capable or need "rescuing"
   - Discriminate in stated salary ranges, qualifications, or opportunities

3. EMPOWERMENT — Language must be positive, respectful, and empowering. Avoid:
   - Condescending or patronising tone ("Even women can…", "For housewives looking for…")
   - Objectifying language or appearance-based criteria
   - Language that reinforces harmful stereotypes

4. CLARITY — The campaign must have a discernible purpose and measurable objective (e.g. registrations, job applications, event attendance). Vague campaigns that cannot be measured are flagged.

5. TRUTHFULNESS — No misleading or exaggerated claims such as:
   - "Guaranteed job placement", "100% salary hike assured"
   - "Approved by Government of India" (without evidence)
   - Fabricated employer names or partnerships

## Scoring Guide
- 90–100 : Excellent. Clearly platform-relevant, empowering, and legally sound.
- 80–89  : Good. Minor tone or clarity issues; acceptable for publishing.
- 60–79  : Needs revision. Has at least one issue that must be fixed before publishing.
- 0–59   : Rejected. Fundamentally not suitable for this platform.

PASS if score >= 80 AND no issues.
BLOCK if score < 80 OR any issue exists.

Be practical and fair. A tech hiring drive targeting women engineers in Bengaluru is 100% compliant. \
A beauty product campaign with no career angle scores < 30. \
A returnee-to-work campaign with one mildly vague sentence might score 78 and be blocked with a clear suggestion.

Always call the validate_campaign_content tool — never reply in plain text."""


# ── Tool schema ───────────────────────────────────────────────────────────────

VALIDATOR_TOOL_SCHEMA = {
    "name": "validate_campaign_content",
    "description": (
        "Record the compliance assessment. Call exactly once with score, gate, "
        "summary, and a list of issues (empty list if compliant)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "score": {
                "type":        "integer",
                "minimum":     0,
                "maximum":     100,
                "description": "Compliance score. 80+ = pass, below 80 = block.",
            },
            "gate": {
                "type":        "string",
                "enum":        ["pass", "block"],
                "description": "'pass' if score>=80 and no issues; 'block' otherwise.",
            },
            "summary": {
                "type":        "string",
                "description": "One sentence verdict, e.g. 'Campaign is career-relevant and compliant.' or 'Campaign must clarify its career-development angle.'",
            },
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {
                            "type":        "string",
                            "description": "Which aspect: brief | headline | body_copy | audience | tone | objective | overall",
                        },
                        "severity": {
                            "type":        "string",
                            "enum":        ["error", "warning"],
                            "description": "error = must fix; warning = should fix",
                        },
                        "message": {
                            "type":        "string",
                            "description": "Plain-English description of the issue and how to fix it.",
                        },
                    },
                    "required": ["field", "severity", "message"],
                },
                "description": "List of compliance issues. Must be empty if gate is 'pass'.",
            },
        },
        "required": ["score", "gate", "summary", "issues"],
    },
}

# ── Anthropic-format wrapper ──────────────────────────────────────────────────
_ANTHROPIC_TOOL = {
    "name":         VALIDATOR_TOOL_SCHEMA["name"],
    "description":  VALIDATOR_TOOL_SCHEMA["description"],
    "input_schema": VALIDATOR_TOOL_SCHEMA["parameters"],
}

# ── OpenAI-format wrapper ─────────────────────────────────────────────────────
_OPENAI_FUNCTION = {
    "type": "function",
    "function": {
        "name":        VALIDATOR_TOOL_SCHEMA["name"],
        "description": VALIDATOR_TOOL_SCHEMA["description"],
        "parameters":  VALIDATOR_TOOL_SCHEMA["parameters"],
    },
}


# ── Validation logic ──────────────────────────────────────────────────────────

def _build_user_message(brief: str, headline: Optional[str], body_copy: Optional[str], campaign_type: Optional[str]) -> str:
    parts = [f"**Brief:**\n{brief}"]
    if campaign_type:
        parts.append(f"**Campaign Type:** {campaign_type}")
    if headline:
        parts.append(f"**Headline:** {headline}")
    if body_copy:
        parts.append(f"**Body Copy:** {body_copy}")
    parts.append("\nAssess this campaign for compliance and call the validate_campaign_content tool.")
    return "\n\n".join(parts)


def validate_content(
    brief: str,
    headline: Optional[str] = None,
    body_copy: Optional[str] = None,
    campaign_type: Optional[str] = None,
) -> ValidationResult:
    """Run AI compliance check. Uses the same LLM_PROVIDER as extraction."""
    user_message = _build_user_message(brief, headline, body_copy, campaign_type)

    if config.LLM_PROVIDER == "anthropic":
        return _validate_anthropic(user_message)
    elif config.LLM_PROVIDER == "openai":
        return _validate_openai(user_message)
    else:
        return ValidationResult(
            ok=False,
            score=0,
            gate="block",
            summary=f"Unsupported LLM_PROVIDER '{config.LLM_PROVIDER}'",
            issues=[],
        )


def _validate_anthropic(user_message: str) -> ValidationResult:
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=[
                {
                    "type":          "text",
                    "text":          VALIDATOR_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[_ANTHROPIC_TOOL],
            tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": user_message}],
        )

        tool_block = next((b for b in response.content if b.type == "tool_use"), None)
        if not tool_block:
            return ValidationResult(
                ok=False, score=0, gate="block",
                summary="Compliance check could not be completed. Please try again.",
                issues=[],
            )

        data = tool_block.input
        issues = [ValidationIssue(**i) for i in data.get("issues", [])]

        return ValidationResult(
            ok=True,
            score=data["score"],
            gate=data["gate"],
            summary=data["summary"],
            issues=issues,
            usage={
                "provider":              "anthropic",
                "model":                 config.ANTHROPIC_MODEL,
                "input_tokens":          response.usage.input_tokens,
                "output_tokens":         response.usage.output_tokens,
                "cache_creation_tokens": getattr(response.usage, "cache_creation_input_tokens", 0),
                "cache_read_tokens":     getattr(response.usage, "cache_read_input_tokens", 0),
            },
        )

    except anthropic.APIStatusError as e:
        return ValidationResult(
            ok=False, score=0, gate="block",
            summary=f"Anthropic API error {e.status_code}: {e.message}",
            issues=[],
        )
    except Exception as e:
        return ValidationResult(ok=False, score=0, gate="block", summary=str(e), issues=[])


def _validate_openai(user_message: str) -> ValidationResult:
    from openai import OpenAI, APIStatusError
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system",  "content": VALIDATOR_SYSTEM_PROMPT},
                {"role": "user",    "content": user_message},
            ],
            tools=[_OPENAI_FUNCTION],
            tool_choice={"type": "function", "function": {"name": VALIDATOR_TOOL_SCHEMA["name"]}},
        )

        message = response.choices[0].message
        if not message.tool_calls:
            return ValidationResult(
                ok=False, score=0, gate="block",
                summary="Compliance check could not be completed. Please try again.",
                issues=[],
            )

        data   = json.loads(message.tool_calls[0].function.arguments)
        issues = [ValidationIssue(**i) for i in data.get("issues", [])]

        return ValidationResult(
            ok=True,
            score=data["score"],
            gate=data["gate"],
            summary=data["summary"],
            issues=issues,
            usage={
                "provider":      "openai",
                "model":         config.OPENAI_MODEL,
                "input_tokens":  response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
        )

    except APIStatusError as e:
        return ValidationResult(
            ok=False, score=0, gate="block",
            summary=f"OpenAI API error {e.status_code}: {e.message}",
            issues=[],
        )
    except Exception as e:
        return ValidationResult(ok=False, score=0, gate="block", summary=str(e), issues=[])
