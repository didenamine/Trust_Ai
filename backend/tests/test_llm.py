"""US05 - the shared LLM layer: strict schema and Groq client (no network: mocked HTTP)."""

import json

import httpx
import pytest

from app.schemas.profile import CandidateProfile
from app.services.cv_analysis_service import PROFILE_EXTRACTION_SCHEMA
from app.services.llm import (
    GroqClient,
    LLMNotConfiguredError,
    LLMRateLimitError,
    LLMResponseError,
    LLMUnavailableError,
    to_strict_json_schema,
)

SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}


# --- Strict schema -------------------------------------------------------------


def _objects(node):
    if isinstance(node, dict):
        if "properties" in node:
            yield node
        for value in node.values():
            yield from _objects(value)
    elif isinstance(node, list):
        for item in node:
            yield from _objects(item)


def test_extraction_schema_is_strict() -> None:
    objects = list(_objects(PROFILE_EXTRACTION_SCHEMA))

    # profile, personal info, skill, experience, education, language, certification, project
    assert len(objects) == 8
    for obj in objects:
        assert obj["additionalProperties"] is False
        assert obj["required"] == list(obj["properties"])


def test_extraction_schema_leaves_out_app_fields_and_validation_keywords() -> None:
    text = json.dumps(PROFILE_EXTRACTION_SCHEMA)

    assert "schema_version" not in PROFILE_EXTRACTION_SCHEMA["properties"]
    assert "language" not in PROFILE_EXTRACTION_SCHEMA["properties"]
    assert '"id"' not in text
    for keyword in ('"pattern"', '"format"', '"maxLength"', '"title"', '"default"'):
        assert keyword not in text
    assert "ContentLanguage" not in PROFILE_EXTRACTION_SCHEMA["$defs"]  # unused once excluded


def test_extraction_schema_has_no_anyof() -> None:
    # Groq's strict mode rejects Pydantic's `anyOf: [X, null]` ("anyOf branches must be
    # disambiguated"): optional values must use a type list instead.
    assert "anyOf" not in json.dumps(PROFILE_EXTRACTION_SCHEMA)


def test_optional_values_are_nullable_type_lists() -> None:
    definitions = PROFILE_EXTRACTION_SCHEMA["$defs"]

    assert definitions["Experience"]["properties"]["company"] == {"type": ["string", "null"]}
    assert definitions["LanguageSkill"]["properties"]["level"] == {
        "type": ["string", "null"],
        "enum": ["A1", "A2", "B1", "B2", "C1", "C2", "native", None],
    }
    # A required enum stays a plain reference.
    assert definitions["Skill"]["properties"]["category"] == {"$ref": "#/$defs/SkillCategory"}


def test_extraction_schema_keeps_fields_named_like_keywords() -> None:
    experience = PROFILE_EXTRACTION_SCHEMA["$defs"]["Experience"]["properties"]

    assert "description" in experience  # a field, not the "description" keyword


def test_strict_schema_does_not_modify_pydantic_schema() -> None:
    before = CandidateProfile.model_json_schema()
    to_strict_json_schema(CandidateProfile, exclude_fields=frozenset({"id"}))

    assert CandidateProfile.model_json_schema() == before


# --- Groq client ---------------------------------------------------------------


def groq_answer(content: str, finish_reason: str = "stop") -> dict:
    return {
        "choices": [
            {"message": {"role": "assistant", "content": content}, "finish_reason": finish_reason}
        ]
    }


def make_client(handler, **kwargs) -> tuple[GroqClient, list[float]]:
    sleeps: list[float] = []
    client = GroqClient(
        api_key=kwargs.pop("api_key", "test-key"),
        model="openai/gpt-oss-120b",
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        **kwargs,
    )
    return client, sleeps


def call(client: GroqClient) -> dict:
    return client.generate_json(system="sys", user="usr", schema=SCHEMA, schema_name="test")


def test_sends_a_strict_json_schema_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=groq_answer('{"ok": true}'))

    client, _ = make_client(handler)

    assert call(client) == {"ok": True}
    request = requests[0]
    assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "usr"},
    ]
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "test", "strict": True, "schema": SCHEMA},
    }
    # Groq's default output limit (3072) cuts a full CV profile off: always set ours.
    assert body["max_completion_tokens"] == 8192
    assert body["reasoning_effort"] == "low"


def test_token_limit_and_reasoning_effort_can_be_left_out() -> None:
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=groq_answer("{}"))

    client, _ = make_client(handler, max_completion_tokens=None, reasoning_effort=None)
    call(client)

    assert "max_completion_tokens" not in bodies[0]
    assert "reasoning_effort" not in bodies[0]


def test_missing_api_key_fails_without_calling_the_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request expected")

    client, _ = make_client(handler, api_key="")

    with pytest.raises(LLMNotConfiguredError):
        call(client)


@pytest.mark.parametrize("status", [401, 403])
def test_rejected_key(status: int) -> None:
    client, _ = make_client(lambda request: httpx.Response(status))

    with pytest.raises(LLMNotConfiguredError):
        call(client)


def test_rate_limit_waits_retry_after_then_succeeds() -> None:
    responses = iter(
        [
            httpx.Response(429, headers={"retry-after": "3"}),
            httpx.Response(200, json=groq_answer('{"ok": true}')),
        ]
    )
    client, sleeps = make_client(lambda request: next(responses))

    assert call(client) == {"ok": True}
    assert sleeps == [3.0]


def test_long_rate_limit_is_reported_instead_of_waiting() -> None:
    client, sleeps = make_client(lambda request: httpx.Response(429, headers={"retry-after": "55"}))

    with pytest.raises(LLMRateLimitError) as info:
        call(client)
    assert info.value.retry_after == 55.0
    assert sleeps == []


def test_rate_limit_after_all_retries() -> None:
    client, sleeps = make_client(lambda request: httpx.Response(429), max_retries=2)

    with pytest.raises(LLMRateLimitError):
        call(client)
    assert sleeps == [1, 2]


def test_server_errors_are_retried() -> None:
    responses = iter(
        [httpx.Response(503), httpx.Response(500), httpx.Response(200, json=groq_answer("{}"))]
    )
    client, sleeps = make_client(lambda request: next(responses), max_retries=2)

    assert call(client) == {}
    assert sleeps == [1, 2]


def test_server_keeps_failing() -> None:
    client, _ = make_client(lambda request: httpx.Response(502), max_retries=1)

    with pytest.raises(LLMUnavailableError):
        call(client)


def test_network_errors_are_retried_then_reported() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=request)

    client, sleeps = make_client(handler, max_retries=1)

    with pytest.raises(LLMUnavailableError):
        call(client)
    assert sleeps == [1]


def test_bad_request_is_a_response_error_with_groq_message() -> None:
    client, _ = make_client(
        lambda request: httpx.Response(
            400, json={"error": {"message": "Generated JSON does not match the expected schema"}}
        )
    )

    with pytest.raises(LLMResponseError, match="does not match the expected schema"):
        call(client)


@pytest.mark.parametrize(
    "body",
    [
        groq_answer("not json"),
        groq_answer("[1, 2]"),
        groq_answer('{"ok": tr', finish_reason="length"),
        {"unexpected": "shape"},
    ],
)
def test_unusable_answers(body: dict) -> None:
    client, _ = make_client(lambda request: httpx.Response(200, json=body))

    with pytest.raises(LLMResponseError):
        call(client)
