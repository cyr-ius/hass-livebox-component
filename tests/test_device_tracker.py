"""The tests for the bbox component."""

import copy
from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant

from tests.const import DEVICES


async def test_device_tracker(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: Generator[AsyncMock | MagicMock],
) -> None:
    """Test reboot button."""
    devices_data = copy.deepcopy(DEVICES)
    AIOSysbus.devices.async_get_devices.return_value = devices_data

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("device_tracker.pc_408")
    assert state is not None
    assert state.state == STATE_HOME
    assert state.attributes.get("ip") == "10.1.2.3"

    devices_data["status"]["wifi"][15]["Active"] = False
    devices_data["status"]["wifi"][15]["IPAddress"] = None
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

        state = hass.states.get("device_tracker.pc_408")
        assert state is not None
        assert state.state == STATE_NOT_HOME
        assert state.attributes.get("ip") is None
