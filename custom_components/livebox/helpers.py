"""Helpers functions."""

import re
from typing import Any

_WIRED_INTERFACE_RE = re.compile(r"eth\d+", re.IGNORECASE)
_WIRELESS_INTERFACE_PREFIXES = ("vap", "wlan", "wl")


def _client_link(device: dict[str, Any]) -> str | None:
    """Return "wifi" or "eth" for the link of a Livebox client, None if unknown.

    The ``wifi`` and ``eth`` tags describe the client link and win over
    ``InterfaceName``, which is the Livebox side of the link: Wi-Fi clients
    of a wired repeater sit on ``ETH*`` (issue #191) and wired clients of a
    Wi-Fi repeater sit on its ``vap*`` backhaul (issue #326).
    """
    tags = device.get("Tags")
    tag_list = tags.split() if isinstance(tags, str) else []
    if "wifi" in tag_list:
        return "wifi"
    if "eth" in tag_list:
        return "eth"
    interface_name = device.get("InterfaceName")
    if not isinstance(interface_name, str):
        return None
    if interface_name.startswith(_WIRELESS_INTERFACE_PREFIXES):
        return "wifi"
    if _WIRED_INTERFACE_RE.fullmatch(interface_name):
        return "eth"
    return None


def is_wireless_device(device: dict[str, Any]) -> bool:
    """Return whether a Livebox device is a Wi-Fi client."""
    return _client_link(device) == "wifi"


def is_wired_device(device: dict[str, Any]) -> bool:
    """Return whether a Livebox device is an Ethernet client."""
    return _client_link(device) == "eth"


def find_item(data: dict[str, Any], key_chain: str, default: Any = None) -> Any:
    """Get recursive key and return value.

    Parameters:
        data (dict[str, Any]) : dictionary to search
        key (str): searched string with dot for key delimited (ex: "key.key.key")
            It is possible to integrate an element of an array
            by indicating its index number
        default (Any): default value to return if key not found
    Returns:
        Any: value of the key or default if not found
    Example:
        >>> find_item({"a": {"b": [{"c": "value_a"},{"d": "value_b"}]}}, "a.b.0.c")
        "value_a"
        >>> find_item({"a": {"b": [{"c": "value"}]}}, "a.b.1.c", "default")
        "default"
    """
    current: Any = data
    for key in key_chain.split("."):
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and key.isdigit() and int(key) < len(current):
            current = current[int(key)]
        else:
            # Missing list index or scalar on the path: the key does not exist.
            current = None
        if current is None:
            break
    return default if current is None and default is not None else current
