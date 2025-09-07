"""Helpers functions."""

from typing import Any


def find_item(data: dict[str, Any], key_chain: str, default: Any = None) -> Any:
    """Get recursive key and return value.

    Parameters:
        data (dict[str, Any]) : dictionary to search
        key (str): searched string with dot for key delimited (ex: "key.key.key")
            It is possible to integrate an element of an array by indicating its index number
        default (Any): default value to return if key not found
    Returns:
        Any: value of the key or default if not found
    Example:
        >>> find_item({"a": {"b": [{"c": "value_a"},{"d": "value_b"}]}}, "a.b.0.c")
        "value_a"
        >>> find_item({"a": {"b": [{"c": "value"}]}}, "a.b.1.c", "default")
        "default"
    """
    if (keys := key_chain.split(".")) and isinstance(keys, list):
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
            elif (
                isinstance(data, list)
                and len(data) > 0
                and key.isdigit()
                and int(key) < len(data)
            ):
                data = data[int(key)]
    return default if data is None and default is not None else data
