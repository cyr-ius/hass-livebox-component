"""Tests for the helper functions."""

import pytest

from custom_components.livebox.helpers import find_item

DATA = {"a": {"b": [{"c": "value"}], "s": "text"}, "ddns": [{"status": "UP"}]}


@pytest.mark.parametrize(
    ("key_chain", "expected"),
    [
        ("a.b.0.c", "value"),
        ("a.s", "text"),
        ("a.missing", "default"),
        ("a.missing.c", "default"),
        ("ddns.1.status", "default"),
        ("a.b.x.c", "default"),
        ("a.s.c", "default"),
    ],
)
def test_find_item(key_chain: str, expected: str) -> None:
    """A missing key anywhere on the path returns the default value."""
    assert find_item(DATA, key_chain, "default") == expected


def test_find_item_without_default() -> None:
    """A missing key returns None when no default is given."""
    assert find_item(DATA, "ddns.1.status") is None
