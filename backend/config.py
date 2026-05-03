"""
Central config — reads .env once at import time.
All other modules import from here instead of calling os.getenv directly.
"""
import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER      = os.getenv("LLM_PROVIDER", "anthropic").lower().strip()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL      = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SUPPORTED_PROVIDERS = {"anthropic", "openai"}


def validate():
    """Call on startup — raises ValueError if config is invalid."""
    if LLM_PROVIDER not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"LLM_PROVIDER='{LLM_PROVIDER}' is not supported. "
            f"Choose one of: {sorted(SUPPORTED_PROVIDERS)}"
        )
    if LLM_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not set in .env")
    if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in .env")
