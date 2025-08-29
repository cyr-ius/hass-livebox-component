import copy
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant
from sqlalchemy import false

from .const import WIFI


@pytest.mark.asyncio
async def test_switch_wifi(
    hass: HomeAssistant, config_entry: ConfigEntry, AIOSysbus: AsyncMock
):
    """Test that the Wi-Fi switch toggles correctly."""
    # --- Test Setup ---
    # Make a deep copy of the fixture data to allow modification in this test
    wifi_data = copy.deepcopy(WIFI)

    # Set initial state to OFF for the guest wifi
    wifi_data["status"]["Enable"] = false
    AIOSysbus.nmc.async_get_wifi.return_value = wifi_data

    # This function will be the side effect of our mock to simulate the state change on the Bbox
    async def mock_set_wireless_guest(enable):
        wifi_data["status"]["Enable"] = True if enable else False

    # Configure the mock to use the side effect
    AIOSysbus.nmc.async_set_wifi.side_effect = mock_set_wireless_guest

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # --- Initial State Check ---
    state = hass.states.get("switch.livebox_7_wifi_switch")
    assert state is not None
    assert state.state == STATE_OFF

    # --- Test Turn On ---
    # Simulate a service call to turn the switch on
    await hass.services.async_call(
        Platform.SWITCH,
        "turn_on",
        {"entity_id": "switch.livebox_7_wifi_switch"},
        blocking=True,
    )
    state = hass.states.get("switch.livebox_7_wifi_switch")

    # --- Assertions ---
    # The state should now be ON because the side_effect updated the data
    # and the turn_on method in the switch entity triggered a coordinator refresh.
    assert state.state == STATE_ON

    # Verify the mock was called correctly
    AIOSysbus.nmc.async_set_wifi.assert_called_once_with(
        {"Enable": True, "Status": True}
    )
