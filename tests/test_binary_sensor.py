"""Tests for the Bbox binary sensor platform."""

import copy
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from .const import WAN_STATUS


@pytest.mark.asyncio
async def test_binary_sensor_link_status(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: Generator[AsyncMock | MagicMock],
):
    """Test the link status binary sensor."""
    # --- Test Setup ---
    # Make a deep copy of the fixture data to allow modification in this test
    info_data = copy.deepcopy(WAN_STATUS)

    # --- Test for ON state ---
    # Set the status to 1 (Connected)
    info_data["data"]["WanState"] = "up"
    AIOSysbus.nmc.async_get_wan_status.return_value = info_data

    # Setup the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the state
    state = hass.states.get("binary_sensor.livebox_7_wan_status")
    assert state is not None
    assert state.state == STATE_ON

    # --- Test for OFF state ---
    # Set the status to 0 (Disconnected)
    info_data["data"]["WanState"] = "down"
    AIOSysbus.nmc.async_get_wan_status.return_value = info_data

    # Trigger a refresh of the coordinator
    coordinator = config_entry.runtime_data
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    # Check the state again
    state = hass.states.get("binary_sensor.livebox_7_wan_status")
    assert state is not None
    assert state.state == STATE_OFF


@pytest.mark.asyncio
async def test_binary_sensor(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: Generator[AsyncMock | MagicMock],
):
    """Test the binary sensor."""

    # Setup the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.livebox_7_call_missed")
    assert state is not None
    assert state.state == STATE_ON

    state = hass.states.get("binary_sensor.livebox_7_remote_access")
    assert state is not None
    assert state.state == STATE_OFF
