"""The tests for the bbox component."""

from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_device_tracker(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: Generator[AsyncMock | MagicMock],
) -> None:
    """Test the device tracker platform."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("device_tracker.pc_408")
    assert state is not None
    assert state.state == STATE_HOME
    assert state.attributes.get("ip") == "10.1.2.3"

    # Disable device PC-408
    AIOSysbus.__devices["status"][69]["Active"] = False
    AIOSysbus.__devices["status"][69]["IPAddress"] = None
    with (
        patch("custom_components.livebox.device_tracker.datetime") as mock_datetime,
    ):
        mock_datetime.today.return_value = datetime(9999, 1, 1, 12, 0, 0)
        mock_datetime.side_effect = lambda *a, **kw: datetime(*a, **kw)

        # Trigger a refresh of the coordinator
        coordinator = config_entry.runtime_data
        await coordinator.async_request_refresh()
        await hass.async_block_till_done()

        state = hass.states.get("device_tracker.pc_408")
        assert state is not None
        assert state.state == STATE_NOT_HOME
        assert state.attributes.get("ip") is None


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_device_tracker_new_device(
    hass,
    config_entry: ConfigEntry,
    AIOSysbus: Generator[AsyncMock | MagicMock],
):
    new_device = {
        "Key": "AA:BB:CC:DD:EE:FF",
        "Name": "New Device",
        "PhysAddress": "AA:BB:CC:DD:EE:FF",
        "IPAddress": "10.10.10.10",
        "Active": True,
        "Tags": "lan edev mac physical wifi flowstats ipv4 ipv6 dhcp ssw_sta events",
    }

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Add new device
    AIOSysbus.__devices["status"].append(new_device)

    # Trigger a refresh of the coordinator

    coordinator = config_entry.runtime_data
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("device_tracker.new_device")
    assert state is not None
    assert state.state == STATE_HOME

    state = hass.states.get("switch.new_device_wan_access")
    assert state is not None
