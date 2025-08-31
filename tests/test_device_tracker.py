"""The tests for the bbox component."""

import copy
from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
)


@pytest.mark.asyncio
async def test_device_tracker(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: Generator[AsyncMock | MagicMock],
) -> None:
    """Test the device tracker platform."""
    devices_data = copy.deepcopy(await AIOSysbus.devices.async_get_devices())
    AIOSysbus.devices.async_get_devices.return_value = devices_data

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(f"device_tracker.{AIOSysbus.__unique_name}_pc_408")
    assert state is not None
    assert state.state == STATE_HOME
    assert state.attributes.get("ip") == "10.1.2.3"

    devices_data["status"]["wifi"][14]["Active"] = False
    devices_data["status"]["wifi"][14]["IPAddress"] = None
    AIOSysbus.devices.async_get_devices.return_value = devices_data

    with (
        patch("custom_components.livebox.device_tracker.datetime") as mock_datetime,
    ):
        mock_datetime.today.return_value = datetime(9999, 1, 1, 12, 0, 0)
        mock_datetime.side_effect = lambda *a, **kw: datetime(*a, **kw)

        # Trigger a refresh of the coordinator
        coordinator = config_entry.runtime_data
        await coordinator.async_request_refresh()
        await hass.async_block_till_done()

        state = hass.states.get(f"device_tracker.{AIOSysbus.__unique_name}_pc_408")
        assert state is not None
        assert state.state == STATE_NOT_HOME
        assert state.attributes.get("ip") is None


@pytest.mark.asyncio
async def test_device_tracker_new_device(
    hass,
    config_entry: ConfigEntry,
    AIOSysbus: Generator[AsyncMock | MagicMock],
):
    calls = []

    new_device = {
        "Key": "AA:BB:CC:DD:EE:FF",
        "Name": "New Device",
        "PhysAddress": "AA:BB:CC:DD:EE:FF",
        "IPAddress": "10.10.10.10",
        "Active": True,
    }

    # Abonne un callback
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data

    async_dispatcher_connect(
        hass, coordinator.signal_device_new, lambda *a: calls.append(a)
    )

    devices_data = copy.deepcopy(await AIOSysbus.devices.async_get_devices())
    devices_data["status"]["wifi"].append(new_device)
    AIOSysbus.devices.async_get_devices.return_value = devices_data

    # Laisse HA traiter
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    assert len(calls) == 1

    # Laisse HA traiter
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(f"device_tracker.{AIOSysbus.__unique_name}_new_device")
    assert state is not None
    assert state.state == STATE_HOME
