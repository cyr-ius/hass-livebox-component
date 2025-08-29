"""Tests for the Bbox sensor platform."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_sensors_state(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
):
    """Test the state of various sensors."""
    # Setup the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(f"sensor.livebox_{AIOSysbus.__model}_fiber_power_rx")
    assert state is not None
    assert float(state.state) == -16.86

    state = hass.states.get(f"sensor.livebox_{AIOSysbus.__model}_fiber_tx")
    assert state is not None
    assert float(state.state) == 1883.81
