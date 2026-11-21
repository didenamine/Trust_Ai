"""In-memory `LLMClient` for tests: no network, answers are given in advance."""

from typing import Any


class FakeLLMClient:
    def __init__(self, *answers: dict[str, Any] | Exception) -> None:
        self._answers = list(answers)
        self.calls: list[dict[str, Any]] = []

    def generate_json(
        self, *, system: str, user: str, schema: dict[str, Any], schema_name: str
    ) -> dict[str, Any]:
        self.calls.append(
            {"system": system, "user": user, "schema": schema, "schema_name": schema_name}
        )
        if not self._answers:
            raise AssertionError("FakeLLMClient has no answer left")
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer
