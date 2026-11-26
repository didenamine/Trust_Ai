"""The interface every LLM provider implements (US05, reused by US09 and US14)."""

from typing import Any, Protocol


class LLMError(Exception):
    """Base class for every LLM failure."""


class LLMNotConfiguredError(LLMError):
    """No API key, or the key is rejected by the provider."""


class LLMUnavailableError(LLMError):
    """The provider can't be reached or keeps failing (network, timeout, 5xx)."""


class LLMRateLimitError(LLMUnavailableError):
    """Too many requests for the current plan."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class LLMResponseError(LLMError):
    """The provider answered, but not with usable JSON."""


class LLMClient(Protocol):
    def generate_json(
        self, *, system: str, user: str, schema: dict[str, Any], schema_name: str
    ) -> dict[str, Any]:
        """Return the model's answer as a JSON object that follows `schema`.

        `schema` must be a strict JSON Schema (see `strict_schema.to_strict_json_schema`).
        The result still has to be validated with Pydantic by the caller.
        """
        ...
