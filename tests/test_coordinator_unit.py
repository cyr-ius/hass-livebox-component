"""Lightweight unit tests for Livebox coordinator topology handling."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from pytest_homeassistant_custom_component.common import load_json_object_fixture

from custom_components.livebox.const import (
    CONF_DISPLAY_DEVICES,
    DEFAULT_DISPLAY_DEVICES,
)
from custom_components.livebox.coordinator import LiveboxDataUpdateCoordinator


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations() -> None:
    """Avoid pulling the Home Assistant test harness into pure unit tests."""


def _load_fixture(name: str) -> dict[str, Any]:
    """Load a typed test fixture."""
    return cast(dict[str, Any], load_json_object_fixture(name))


def _tags(device: dict[str, Any]) -> str:
    """Return device tags as a string for test filtering."""
    return cast(str, device.get("Tags", ""))


def _devices_response_from_issue_191(
    devices: dict[str, Any], parameters: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Reconstruct the minimal device-query responses used by the integration."""
    if parameters is None:
        return devices

    status = cast(list[dict[str, Any]], devices["status"])

    if parameters in (
        {
            "expression": {
                "wifi": 'wifi && (edev || hnid) and .PhysAddress!=""',
                "eth": 'eth && (edev || hnid) and .PhysAddress!=""',
            }
        },
        {
            "expression": {
                "wifi": '.Active==true && wifi && (edev || hnid) and .PhysAddress!=""',
                "eth": '.Active==true && eth && (edev || hnid) and .PhysAddress!=""',
            }
        },
    ):
        return {
            "status": {
                "wifi": [
                    item
                    for item in status
                    if ("edev" in _tags(item) or "hnid" in _tags(item))
                    and "wifi" in _tags(item)
                    and item.get("PhysAddress") is not None
                ],
                "eth": [
                    item
                    for item in status
                    if ("edev" in _tags(item) or "hnid" in _tags(item))
                    and "eth" in _tags(item)
                    and item.get("PhysAddress") is not None
                ],
            }
        }

    return {}


def _build_issue_191_coordinator() -> LiveboxDataUpdateCoordinator:
    """Return a coordinator wired to the repeater topology fixture."""
    issue_191 = _load_fixture("issue_191_repeater_topology_sanitized.json")["api_raw"]
    devices = issue_191["Devices.async_get_devices"]

    coordinator = object.__new__(LiveboxDataUpdateCoordinator)
    coordinator.config_entry = SimpleNamespace(
        options={CONF_DISPLAY_DEVICES: DEFAULT_DISPLAY_DEVICES}
    )
    coordinator._topology_cache = ({}, {})
    coordinator._topology_cache_at = None
    coordinator._topology_last_update = None
    coordinator.api = SimpleNamespace(
        devices=SimpleNamespace(async_get_devices=object()),
        topologydiagnostics=SimpleNamespace(
            async_get_topodiags=object(),
            async_set_topodiags_build=object(),
        ),
    )

    async def _make_request(func: Any, parameters: Any = None) -> dict[str, Any]:
        if func is coordinator.api.topologydiagnostics.async_get_topodiags:
            return issue_191["TopologyDiagnostics.async_get_topodiags"]
        if func is coordinator.api.topologydiagnostics.async_set_topodiags_build:
            return issue_191["TopologyDiagnostics.async_set_topodiags_build"]
        if func is coordinator.api.devices.async_get_devices:
            return _devices_response_from_issue_191(devices, parameters)
        raise AssertionError("Unexpected API call")

    coordinator._make_request = cast(Any, _make_request)
    return coordinator


async def test_async_get_devices_keeps_repeaters_without_lan_tracking() -> None:
    """Repeaters should stay tracked so clients can attach via_device."""
    coordinator = _build_issue_191_coordinator()

    _, topology_repeaters = await LiveboxDataUpdateCoordinator.async_get_topology(
        coordinator
    )
    tracked_devices, counters = await LiveboxDataUpdateCoordinator.async_get_devices(
        coordinator,
        lan_tracking=False,
        wifi_tracking=True,
        repeater_keys=set(topology_repeaters),
    )

    assert counters == {"wireless": 4, "wired": 0}
    assert "CC:CC:CC:CC:CC:01" in tracked_devices
    assert "BB:BB:BB:BB:BB:01" not in tracked_devices


async def test_async_get_devices_skips_repeaters_when_tracking_disabled() -> None:
    """When both tracking modes are off, no device trackers should be created."""
    coordinator = _build_issue_191_coordinator()

    _, topology_repeaters = await LiveboxDataUpdateCoordinator.async_get_topology(
        coordinator
    )
    tracked_devices, counters = await LiveboxDataUpdateCoordinator.async_get_devices(
        coordinator,
        lan_tracking=False,
        wifi_tracking=False,
        repeater_keys=set(topology_repeaters),
    )

    assert tracked_devices == {}
    assert counters == {"wireless": 0, "wired": 0}


async def test_async_get_topology_returns_cached_value_on_invalid_status() -> None:
    """Malformed topology status should fall back to the existing cache."""
    coordinator = object.__new__(LiveboxDataUpdateCoordinator)
    coordinator.config_entry = SimpleNamespace(options={})
    coordinator._topology_cache = (
        {"DD:DD:DD:DD:DD:01": "CC:CC:CC:CC:CC:01"},
        {"CC:CC:CC:CC:CC:01": "Repeater-1"},
    )
    coordinator._topology_cache_at = None
    coordinator._topology_last_update = None
    coordinator.api = SimpleNamespace(
        topologydiagnostics=SimpleNamespace(
            async_get_topodiags=object(),
            async_set_topodiags_build=object(),
        )
    )

    async def _make_request(func: Any, parameters: Any = None) -> dict[str, Any]:
        if func is coordinator.api.topologydiagnostics.async_get_topodiags:
            return {"status": []}
        raise AssertionError("Topology rebuild should not be attempted")

    coordinator._make_request = cast(Any, _make_request)

    assert await LiveboxDataUpdateCoordinator.async_get_topology(coordinator) == (
        {"DD:DD:DD:DD:DD:01": "CC:CC:CC:CC:CC:01"},
        {"CC:CC:CC:CC:CC:01": "Repeater-1"},
    )
