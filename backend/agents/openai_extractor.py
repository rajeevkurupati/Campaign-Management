"""
OpenAI extraction agent.
Uses function_calling with the same tool schema as the Anthropic agent.
"""
import json
import openai
from config import OPENAI_API_KEY, OPENAI_MODEL
from agents._prompt import SYSTEM_PROMPT, OPENAI_FUNCTION
from models.campaign import ExtractedCampaign, ExtractResponse

_client = openai.OpenAI(api_key=OPENAI_API_KEY)


def extract_campaign(brief: str) -> ExtractResponse:
    try:
        response = _client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=1024,
            tools=[OPENAI_FUNCTION],
            tool_choice={"type": "function", "function": {"name": "extract_campaign_details"}},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Extract campaign details from this brief:\n\n{brief}",
                },
            ],
        )

        message = response.choices[0].message

        # Grab the function call result
        if not message.tool_calls:
            return ExtractResponse(
                ok=False,
                error="OpenAI did not call the extraction function. Please try again.",
            )

        fn_args = json.loads(message.tool_calls[0].function.arguments)
        campaign = ExtractedCampaign(**fn_args)

        usage = response.usage
        return ExtractResponse(
            ok=True,
            data=campaign,
            usage={
                "provider":       "openai",
                "model":          OPENAI_MODEL,
                "input_tokens":   usage.prompt_tokens if usage else 0,
                "output_tokens":  usage.completion_tokens if usage else 0,
                # OpenAI doesn't have prompt caching on these tiers; report 0
                "cache_creation_tokens": 0,
                "cache_read_tokens":     getattr(
                    getattr(usage, "prompt_tokens_details", None),
                    "cached_tokens", 0
                ),
            },
        )

    except openai.APIStatusError as e:
        return ExtractResponse(ok=False, error=f"OpenAI API error {e.status_code}: {e.message}")
    except Exception as e:
        return ExtractResponse(ok=False, error=str(e))
