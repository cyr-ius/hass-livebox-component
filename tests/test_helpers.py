"""Tests for the helper functions."""

import pytest

from custom_components.livebox.helpers import (
    find_item,
    is_wired_device,
    is_wireless_device,
)

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


@pytest.mark.parametrize(
    ("interface", "wireless", "wired"),
    [
        ("vap5g0priv", True, False),
        ("wl0", True, False),
        ("ETH2", False, True),
        ("bridge", False, False),
        (None, False, False),
    ],
)
def test_link_from_interface_name(
    interface: str | None, wireless: bool, wired: bool
) -> None:
    """Without wifi/eth tag, the link comes from the Livebox interface name."""
    device = {"Tags": "lan edev", "InterfaceName": interface}
    assert is_wireless_device(device) is wireless
    assert is_wired_device(device) is wired
