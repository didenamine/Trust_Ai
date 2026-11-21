"""Groq implementation of `LLMClient`, through its OpenAI-compatible API.

Uses strict structured outputs (`response_format.type = "json_schema"`, `strict: true`),
which Groq guarantees for some models only, e.g. `openai/gpt-oss-120b` and
`openai/gpt-oss-20b`: https://console.groq.com/docs/structured-outputs
"""

import json
import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

from app.services.llm.base import (
    LLMNotConfiguredError,
    LLMRateLimitError,
    LLMResponseError,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)

# Never wait longer than this for a rate limit inside a request: better to tell the user.
_MAX_RETRY_WAIT_SECONDS = 20.0


class GroqClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.groq.com/openai/v1",
        timeout: float = 60.0,
        max_retries: int = 2,
        max_completion_tokens: int | None = 8192,
        reasoning_effort: str | None = "low",
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """
        max_completion_tokens: Groq's default (3072 for gpt-oss) is too small for a full
            CV: reasoning + JSON get cut off and strict mode rejects the answer.
        reasoning_effort: "low" / "medium" / "high" for reasoning models (gpt-oss). Data
            extraction needs little reasoning, and fewer tokens means fewer rate limits.
            None for models that don't support it.
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_completion_tokens = max_completion_tokens
        self.reasoning_effort = reasoning_effort
        self._transport = transport
        self._sleep = sleep

    def generate_json(
        self, *, system: str, user: str, schema: dict[str, Any], schema_name: str
    ) -> dict[str, Any]:
        if not self.api_key:
            raise LLMNotConfiguredError("LLM_API_KEY is not set")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
        }
        if self.max_completion_tokens:
            payload["max_completion_tokens"] = self.max_completion_tokens
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        body = self._post_with_retries("/chat/completions", payload)
        return _parse_json_answer(body)

    def _post_with_retries(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(
            base_url=self.base_url, timeout=self.timeout, transport=self._transport
        ) as client:
            for attempt in range(self.max_retries + 1):
                is_last_attempt = attempt == self.max_retries
                try:
                    response = client.post(path, json=payload, headers=headers)
                except httpx.TransportError as exc:  # includes timeouts
                    logger.warning("Groq request failed (attempt %d): %s", attempt + 1, exc)
                    if is_last_attempt:
                        raise LLMUnavailableError(str(exc)) from exc
                    self._sleep(2**attempt)
                    continue

                if response.status_code == 429:
                    retry_after = _retry_after_seconds(response)
                    if is_last_attempt or (retry_after or 0) > _MAX_RETRY_WAIT_SECONDS:
                        raise LLMRateLimitError("Groq rate limit reached", retry_after)
                    self._sleep(retry_after if retry_after is not None else 2**attempt)
                    continue

                if response.status_code >= 500:
                    logger.warning(
                        "Groq returned %d (attempt %d)", response.status_code, attempt + 1
                    )
                    if is_last_attempt:
                        raise LLMUnavailableError(f"Groq returned {response.status_code}")
                    self._sleep(2**attempt)
                    continue

                if response.status_code in (401, 403):
                    raise LLMNotConfiguredError("Groq rejected the API key")

                if response.status_code >= 400:
                    raise LLMResponseError(
                        f"Groq returned {response.status_code}: {_error_message(response)}"
                    )

                return response.json()

        raise AssertionError("unreachable")  # pragma: no cover


def _parse_json_answer(body: dict[str, Any]) -> dict[str, Any]:
    try:
        choice = body["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMResponseError("Unexpected response shape") from exc

    if choice.get("finish_reason") == "length":
        raise LLMResponseError("The answer was cut off (output token limit reached)")
    try:
        data = json.loads(content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LLMResponseError("The answer is not valid JSON") from exc
    if not isinstance(data, dict):
        raise LLMResponseError("The answer is not a JSON object")
    return data


def _retry_after_seconds(response: httpx.Response) -> float | None:
    try:
        return float(response.headers["retry-after"])
    except (KeyError, ValueError):
        return None


def _error_message(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["message"])
    except (ValueError, KeyError, TypeError):
        return response.text[:200]
