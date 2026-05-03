"""
Provider factory — routes extraction calls to the correct LLM backend.

The active provider is read from config.LLM_PROVIDER (set via .env).
Adding a new provider only requires:
  1. A new <provider>_extractor.py with an extract_campaign(brief) function
  2. A new branch in the factory below
"""
from config import LLM_PROVIDER
from models.campaign import ExtractResponse


def extract_campaign(brief: str) -> ExtractResponse:
    """Delegate to the configured provider's extraction agent."""

    if LLM_PROVIDER == "anthropic":
        from agents.anthropic_extractor import extract_campaign as _extract
    elif LLM_PROVIDER == "openai":
        from agents.openai_extractor import extract_campaign as _extract
    else:
        return ExtractResponse(
            ok=False,
            error=f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}'. "
                  "Set LLM_PROVIDER=anthropic or LLM_PROVIDER=openai in .env",
        )

    return _extract(brief)
