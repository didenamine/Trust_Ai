"""LLM access shared by every feature (US05 CV analysis, US09 offer analysis, US14...).

Usage in a route:

    from app.services.llm import LLMClient, get_llm_client

    def my_route(llm: LLMClient = Depends(get_llm_client)): ...

In tests, override `get_llm_client` with a `FakeLLMClient`.
"""

from app.core.config import get_settings
from app.services.llm.base import (
    LLMClient,
    LLMError,
    LLMNotConfiguredError,
    LLMRateLimitError,
    LLMResponseError,
    LLMUnavailableError,
)
from app.services.llm.groq import GroqClient
from app.services.llm.strict_schema import to_strict_json_schema


def get_llm_client() -> LLMClient:
    """FastAPI dependency: the configured provider (Groq)."""
    settings = get_settings()
    return GroqClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        max_completion_tokens=settings.llm_max_completion_tokens or None,
        reasoning_effort=settings.llm_reasoning_effort or None,
    )


__all__ = [
    "GroqClient",
    "LLMClient",
    "LLMError",
    "LLMNotConfiguredError",
    "LLMRateLimitError",
    "LLMResponseError",
    "LLMUnavailableError",
    "get_llm_client",
    "to_strict_json_schema",
]
