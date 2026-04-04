"""The tests for the bbox component."""

from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.livebox.const import DOMAIN
from custom_components.livebox.coordinator import LiveboxDataUpdateCoordinator
from custom_components.livebox.device_tracker import async_add_new_tracked_entities


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_device_tracker(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
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
    AIOSysbus: AsyncMock | MagicMock,
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


async def test_device_tracker_adds_repeaters_before_clients(
) -> None:
    """Create repeater entities before their children and set via_device."""
    def _get_parent_device_identifier(device_key: str | None) -> tuple[str, str]:
        if device_key == "DD:DD:DD:DD:DD:01":
            return (DOMAIN, "CC:CC:CC:CC:CC:01")
        return (DOMAIN, "LIVEBOX-1")

    coordinator = cast(
        LiveboxDataUpdateCoordinator,
        SimpleNamespace(
            unique_id="LIVEBOX-1",
            config_entry=SimpleNamespace(
                data={"host": "192.168.1.1", "port": 80},
                options={},
            ),
            get_parent_device_identifier=_get_parent_device_identifier,
            data={
                "infos": {"ProductClass": "Livebox 7"},
                "devices": {
                    "DD:DD:DD:DD:DD:01": {
                        "Key": "DD:DD:DD:DD:DD:01",
                        "Name": "Device-Repeater-5g-1",
                        "IPAddress": "192.168.1.21",
                    },
                    "CC:CC:CC:CC:CC:01": {
                        "Key": "CC:CC:CC:CC:CC:01",
                        "Name": "Repeater-1",
                        "IPAddress": "192.168.1.39",
                        "DeviceType": "repeteurwifi6",
                    },
                    "AA:AA:AA:AA:AA:01": {
                        "Key": "AA:AA:AA:AA:AA:01",
                        "Name": "Device-Direct-5g-1",
                        "IPAddress": "192.168.1.14",
                    },
                },
                "topology_repeaters": {"CC:CC:CC:CC:CC:01": "Repeater-1"},
                "topology_via_device": {"DD:DD:DD:DD:DD:01": "CC:CC:CC:CC:CC:01"},
            },
        ),
    )

    created = []

    def _add_entities(new_entities: Any) -> None:
        entities = cast(list[Any], new_entities)
        created.extend(entities)

    async_add_new_tracked_entities(
        coordinator,
        cast(AddEntitiesCallback, _add_entities),
        set(),
    )

    assert [entity._device["Key"] for entity in created] == [
        "CC:CC:CC:CC:CC:01",
        "DD:DD:DD:DD:DD:01",
        "AA:AA:AA:AA:AA:01",
    ]
    assert created[0].device_info is not None
    assert created[0].device_info["via_device"] == (DOMAIN, "LIVEBOX-1")
    assert created[1].device_info is not None
    assert created[1].device_info["via_device"] == (DOMAIN, "CC:CC:CC:CC:CC:01")
