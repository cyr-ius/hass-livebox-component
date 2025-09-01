import copy
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from sqlalchemy import false


@pytest.mark.parametrize("AIOSysbus", ["5", "7", "7.1"], indirect=True)
async def test_switch_wifi(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
    service_calls: list[ServiceCall],
):
    """Test that the Wi-Fi switch toggles correctly."""
    # --- Test Setup ---
    # Make a deep copy of the fixture data to allow modification in this test
    wifi_data = copy.deepcopy(await AIOSysbus.nmc.async_get_wifi())

    # Set initial state to OFF for the guest wifi
    wifi_data["status"]["Enable"] = false
    AIOSysbus.nmc.async_get_wifi.return_value = wifi_data

    # This function will be the side effect of our mock to simulate the state change on the Bbox
    async def mock_set_wireless_guest(enable):
        wifi_data["status"]["Enable"] = True if enable else False

    # Configure the mock to use the side effect
    AIOSysbus.nmc.async_set_wifi.side_effect = mock_set_wireless_guest
    AIOSysbus.nemo.async_wifi.side_effect = mock_set_wireless_guest  # Livebox 5

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # --- Initial State Check ---
    state = hass.states.get(f"switch.{AIOSysbus.__unique_name}_wifi")
    assert state is not None
    assert state.state == STATE_OFF

    # --- Test Turn On ---
    # Simulate a service call to turn the switch on
    data = {
        ATTR_ENTITY_ID: f"switch.{AIOSysbus.__unique_name}_wifi",
    }
    await hass.services.async_call(Platform.SWITCH, "turn_on", data, blocking=True)

    assert len(service_calls) == 1

    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(f"switch.{AIOSysbus.__unique_name}_wifi")
    assert state.state == STATE_ON


@pytest.mark.parametrize("AIOSysbus", ["5", "7", "7.1"], indirect=True)
async def test_switch_guest_wifi(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
    service_calls: list[ServiceCall],
):
    """Test that the Wi-Fi switch toggles correctly."""
    # --- Test Setup ---
    # Make a deep copy of the fixture data to allow modification in this test
    wifi_data = copy.deepcopy(await AIOSysbus.nmc.async_get_guest_wifi())

    # Set initial state to OFF for the guest wifi
    wifi_data["status"]["Enable"] = false
    AIOSysbus.nmc.async_get_guest_wifi.return_value = wifi_data

    # This function will be the side effect of our mock to simulate the state change on the Bbox
    async def mock_set_wireless_guest(enable):
        wifi_data["status"]["Enable"] = True if enable else False

    # Configure the mock to use the side effect
    AIOSysbus.nmc.async_set_guest_wifi.side_effect = mock_set_wireless_guest
    AIOSysbus.nmc.async_guest_wifi.side_effect = mock_set_wireless_guest  # Livebox 5

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # --- Initial State Check ---
    state = hass.states.get(f"switch.{AIOSysbus.__unique_name}_guest_wifi")
    assert state is not None
    assert state.state == STATE_OFF

    # --- Test Turn On ---
    # Simulate a service call to turn the switch on
    data = {
        ATTR_ENTITY_ID: f"switch.{AIOSysbus.__unique_name}_guest_wifi",
    }
    await hass.services.async_call(Platform.SWITCH, "turn_on", data, blocking=True)

    assert len(service_calls) == 1

    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(f"switch.{AIOSysbus.__unique_name}_guest_wifi")
    assert state.state == STATE_ON


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_switch_wan_access(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
    service_calls: list[ServiceCall],
):
    """Test that the Wi-Fi switch toggles correctly."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # --- Initial State Check ---
    state = hass.states.get("switch.pc_408_wan_access")
    assert state is not None
    assert state.state == STATE_ON

    # --- Test Turn On ---
    # Simulate a service call to turn the switch on
    data = {
        ATTR_ENTITY_ID: "switch.pc_408_wan_access",
    }
    await hass.services.async_call(Platform.SWITCH, "turn_on", data, blocking=True)

    assert len(service_calls) == 1
