"""Tests for the Livebox coordinator."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import load_json_object_fixture

from custom_components.livebox.coordinator import LiveboxDataUpdateCoordinator


def _load_fixture(name: str) -> dict[str, Any]:
    """Load a typed test fixture."""
    return cast(dict[str, Any], load_json_object_fixture(name))


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_async_get_devices_matches_issue_233_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Test device counts using a sanitized issue #233 diagnostics fixture."""
    fixture = _load_fixture("issue_233_livebox_6_diagnostics_sanitized.json")
    query_key = (
        "Devices.async_get_devices::{'expression': {'wifi': "
        "'wifi && (edev || hnid) and .PhysAddress!=\"\"', 'eth': "
        "'eth && (edev || hnid) and .PhysAddress!=\"\"'}}"
    )
    query_response = fixture["data"]["api_raw"][query_key]
    expected_wireless = len(query_response["status"]["wifi"])
    expected_wired = len(query_response["status"]["eth"])

    coordinator = LiveboxDataUpdateCoordinator(hass, config_entry)
    await coordinator._async_setup()

    AIOSysbus.devices.async_get_devices.side_effect = None
    AIOSysbus.devices.async_get_devices.return_value = query_response

    _, counters = await coordinator.async_get_devices(
        lan_tracking=True, wifi_tracking=True
    )

    assert counters == {"wireless": expected_wireless, "wired": expected_wired}
