"""Tests for the Bbox sensor platform."""

from unittest.mock import AsyncMock

import homeassistant.helpers.entity_registry as er
import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


@pytest.mark.parametrize("AIOSysbus", ["5", "7", "7.1"], indirect=True)
async def test_sensors_state(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
):
    """Test the state of various sensors."""
    # Setup the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_power_tx")
    assert state is not None
    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_power_rx")
    assert state is not None

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_tx")
    assert state is not None
    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_rx")
    assert state is not None

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_callers")
    assert state is not None
    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_ports_forwarding")
    assert state is not None
    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_dhcp_leases")
    assert state is not None
    assert int(state.state) >= 0
    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_guest_dhcp_leases")
    assert state is not None
    assert int(state.state) >= 0

    # entity_registry_enabled_default=False
    state = er.async_get(hass).async_get(f"sensor.{AIOSysbus.__unique_name}_wifi_tx")
    assert state is not None
    state = er.async_get(hass).async_get(f"sensor.{AIOSysbus.__unique_name}_wifi_rx")
    assert state is not None
