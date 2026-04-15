"""Helpers functions."""

from typing import Any


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
    if (keys := key_chain.split(".")) and isinstance(keys, list):
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif (
                isinstance(current, list)
                and len(current) > 0
                and key.isdigit()
                and int(key) < len(current)
            ):
                current = current[int(key)]
    return default if current is None and default is not None else current
