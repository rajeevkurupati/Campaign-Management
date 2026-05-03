"""
Anthropic (Claude) extraction agent.
Uses tool_use with a cached system prompt for efficiency.
"""
import anthropic
from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from agents._prompt import SYSTEM_PROMPT, EXTRACT_TOOL
from models.campaign import ExtractedCampaign, ExtractResponse

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def extract_campaign(brief: str) -> ExtractResponse:
    try:
        response = _client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},  # billed once per 5-min window
                }
            ],
            tools=[EXTRACT_TOOL],
            tool_choice={"type": "auto"},
            messages=[
                {
                    "role": "user",
                    "content": f"Extract campaign details from this brief:\n\n{brief}",
                }
            ],
        )

        tool_block = next(
            (b for b in response.content if b.type == "tool_use"), None
        )
        if not tool_block:
            return ExtractResponse(
                ok=False,
                error="Claude did not call the extraction tool. Please try again.",
            )

        campaign = ExtractedCampaign(**tool_block.input)

        return ExtractResponse(
            ok=True,
            data=campaign,
            usage={
                "provider":              "anthropic",
                "model":                 ANTHROPIC_MODEL,
                "input_tokens":          response.usage.input_tokens,
                "output_tokens":         response.usage.output_tokens,
                "cache_creation_tokens": getattr(response.usage, "cache_creation_input_tokens", 0),
                "cache_read_tokens":     getattr(response.usage, "cache_read_input_tokens", 0),
            },
        )

    except anthropic.APIStatusError as e:
        return ExtractResponse(ok=False, error=f"Anthropic API error {e.status_code}: {e.message}")
    except Exception as e:
        return ExtractResponse(ok=False, error=str(e))
