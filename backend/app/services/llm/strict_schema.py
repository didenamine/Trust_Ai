"""Turn a Pydantic model into a JSON Schema usable in strict structured-output mode.

Strict mode (Groq, OpenAI) guarantees the answer matches the schema, but requires:
every property listed in `required` (optional ones are nullable instead) and
`additionalProperties: false` on every object. Validation keywords such as
`pattern`, `format` or `maxLength` are removed: Pydantic checks them afterwards anyway,
and leaving them out keeps the schema small (it counts as input tokens).
"""

import copy
from typing import Any

from pydantic import BaseModel

_DROPPED_KEYWORDS = {
    "title",
    "default",
    "description",
    "examples",
    "format",
    "pattern",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "const",
}


def to_strict_json_schema(
    model: type[BaseModel], *, exclude_fields: frozenset[str] = frozenset()
) -> dict[str, Any]:
    """JSON Schema of `model` in strict form, without the fields in `exclude_fields`
    (at any depth), e.g. ids that the application generates itself."""
    schema = copy.deepcopy(model.model_json_schema())
    _make_strict(schema, exclude_fields)
    _collapse_nullable(schema, schema.get("$defs", {}))
    _drop_unused_definitions(schema)
    return schema


def _collapse_nullable(node: Any, definitions: dict[str, Any]) -> None:
    """Rewrite Pydantic's `anyOf: [X, {"type": "null"}]` without `anyOf`.

    Groq's strict mode only accepts an `anyOf` whose branches can be told apart by a
    required discriminator, so optional values are written the way its docs recommend:
    `{"type": ["string", "null"]}`, and an optional enum lists `null` among its values.
    """
    if isinstance(node, list):
        for item in node:
            _collapse_nullable(item, definitions)
        return
    if not isinstance(node, dict):
        return

    branches = node.get("anyOf")
    if isinstance(branches, list) and len(branches) == 2 and {"type": "null"} in branches:
        other = next(branch for branch in branches if branch != {"type": "null"})
        ref = other.get("$ref", "")
        target = definitions.get(ref.removeprefix("#/$defs/")) if ref else other
        if isinstance(target, dict) and "enum" in target:
            del node["anyOf"]
            node["type"] = [target.get("type", "string"), "null"]
            node["enum"] = [*target["enum"], None]
        elif isinstance(target, dict) and isinstance(target.get("type"), str) and not ref:
            del node["anyOf"]
            node.update({**other, "type": [other["type"], "null"]})

    for value in node.values():
        _collapse_nullable(value, definitions)


def _make_strict(node: Any, exclude_fields: frozenset[str]) -> None:
    if isinstance(node, list):
        for item in node:
            _make_strict(item, exclude_fields)
        return
    if not isinstance(node, dict):
        return

    for keyword in _DROPPED_KEYWORDS & node.keys():
        # "title" / "description" etc. are also legitimate *property names*: only drop
        # them when they are schema keywords, i.e. not inside a "properties" mapping.
        if not isinstance(node[keyword], dict) or keyword in {"default", "examples", "const"}:
            del node[keyword]

    properties = node.get("properties")
    if isinstance(properties, dict):
        for name in exclude_fields & properties.keys():
            del properties[name]
        node["required"] = list(properties)
        node["additionalProperties"] = False
        node["type"] = "object"
        for subschema in properties.values():
            _make_strict(subschema, exclude_fields)

    for key, value in node.items():
        if key != "properties":
            _make_strict(value, exclude_fields)


def _drop_unused_definitions(schema: dict[str, Any]) -> None:
    definitions = schema.get("$defs", {})
    used: set[str] = set()

    def collect(node: Any) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                name = ref.removeprefix("#/$defs/")
                if name not in used:
                    used.add(name)
                    collect(definitions.get(name))
            for key, value in node.items():
                if key != "$defs":
                    collect(value)
        elif isinstance(node, list):
            for item in node:
                collect(item)

    collect(schema)
    for name in set(definitions) - used:
        del definitions[name]
    if "$defs" in schema and not definitions:
        del schema["$defs"]
