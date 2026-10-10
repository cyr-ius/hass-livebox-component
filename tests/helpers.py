"""Shared helpers for the Livebox tests."""

import re
from typing import Any, cast

from pytest_homeassistant_custom_component.common import load_json_object_fixture

_TOKEN_RE = re.compile(
    r'\(|\)|&&|\|\||\band\b|\bor\b|\.\w+\s*(?:==|!=)\s*(?:"[^"]*"|\w+)|\w+'
)
_FIELD_RE = re.compile(r'\.(\w+)\s*(==|!=)\s*("[^"]*"|\w+)')


def load_fixture(name: str) -> dict[str, Any]:
    """Load a typed test fixture."""
    return cast(dict[str, Any], load_json_object_fixture(name))


def load_api_fixture(name: str) -> dict[str, Any]:
    """Load the raw API payload of a test fixture."""
    return cast(dict[str, Any], load_fixture(name)["api_raw"])


def _field_matches(device: dict[str, Any], token: str) -> bool:
    """Evaluate a `.Field==value` / `.Field!=value` condition."""
    match = _FIELD_RE.fullmatch(token)
    if match is None:
        raise ValueError(f"Unsupported condition: {token}")
    field, operator, raw = match.groups()
    expected: Any
    if raw.startswith('"'):
        expected = raw[1:-1]
    else:
        expected = {"true": True, "false": False}.get(raw, raw)
    value = device.get(field)
    if value is None and isinstance(expected, str):
        value = ""
    return (value == expected) == (operator == "==")


def match_expression(device: dict[str, Any], expression: str) -> bool:
    """Evaluate a Livebox device-query expression against a device.

    Supports tags, `&&`/`and`, `||`/`or`, parentheses and field comparisons,
    which is the subset used by the integration.
    """
    tags = set(cast(str, device.get("Tags", "")).split())
    tokens = _TOKEN_RE.findall(expression)
    pos = 0

    def _peek() -> str | None:
        return tokens[pos] if pos < len(tokens) else None

    def _next() -> str:
        nonlocal pos
        pos += 1
        return tokens[pos - 1]

    def _or() -> bool:
        result = _and()
        while _peek() in ("||", "or"):
            _next()
            result = _and() or result
        return result

    def _and() -> bool:
        result = _atom()
        while _peek() in ("&&", "and"):
            _next()
            result = _atom() and result
        return result

    def _atom() -> bool:
        token = _next()
        if token == "(":
            result = _or()
            if _next() != ")":
                raise ValueError(f"Unbalanced expression: {expression}")
            return result
        if token.startswith("."):
            return _field_matches(device, token)
        return token in tags

    result = _or()
    if pos != len(tokens):
        raise ValueError(f"Unexpected token in expression: {expression}")
    return result


def devices_response(
    devices: list[dict[str, Any]], parameters: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Emulate `Devices.async_get_devices` for the given raw device list."""
    if parameters is None:
        return {"status": devices}
    expressions = cast(dict[str, str], parameters.get("expression", {}))
    return {
        "status": {
            name: [device for device in devices if match_expression(device, expr)]
            for name, expr in expressions.items()
        }
    }
