import logging
import os
from typing import Optional

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv()

DEFAULT_MODEL = "gemini-2.5-flash"


def _ensure_api_key() -> None:
    """Raise a clear error if GOOGLE_API_KEY is missing."""
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Add it to your .env file to enable live Gemini calls."
        )


def get_gemini_chat(model: Optional[str] = None, temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    """
    Centralized Gemini chat client.

    All components should use this helper instead of instantiating ChatGoogleGenerativeAI directly.
    """
    _ensure_api_key()
    model_name = model or DEFAULT_MODEL
    logging.info(
        "[GeminiService] Initializing Gemini chat client",
        extra={"model": model_name, "temperature": temperature},
    )
    return ChatGoogleGenerativeAI(model=model_name, temperature=temperature)


def is_live_mode() -> bool:
    """
    Return True if the system is configured to use live Gemini instead of mock data.

    This reads USE_MOCK_DATA directly from the process environment (with .env already loaded),
    so there is no confusion about import order.
    """
    raw = os.getenv("USE_MOCK_DATA", "1").strip().lower()
    # Same truthy convention as config.py, but inverted: live mode when mock flag is false-y.
    is_mock = raw in ("1", "true", "yes")
    return not is_mock

