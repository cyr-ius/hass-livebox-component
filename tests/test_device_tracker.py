"""The tests for the bbox component."""

from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.livebox.const import (
    CONF_TRACKING_TIMEOUT,
    DEFAULT_TRACKING_TIMEOUT,
    DOMAIN,
)
from custom_components.livebox.coordinator import LiveboxDataUpdateCoordinator
from custom_components.livebox.device_tracker import (
    LiveboxDeviceScannerEntity,
    async_add_new_tracked_entities,
)


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
    assert state.attributes.get("connection") == "wifi"
    assert state.attributes.get("frequency_band") == "5GHz"
    assert state.attributes.get("signal_quality") is not None
    assert "last_data_downlink_rate" not in state.attributes
    assert "last_data_uplink_rate" not in state.attributes
    assert "signal_noise_ratio" not in state.attributes
    assert "avg_signal_strength_by_chain" not in state.attributes
    assert "link_bandwidth" not in state.attributes
    assert "signal_strength" not in state.attributes

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


async def test_device_tracker_adds_repeaters_before_clients() -> None:
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


def test_device_tracker_adds_associated_wifi_stats() -> None:
    """Wi-Fi device trackers should keep only contextual attributes."""

    coordinator = cast(
        LiveboxDataUpdateCoordinator,
        SimpleNamespace(
            data={
                "lan": [
                    {
                        "type": "Wireless",
                        "name": "5GHz (home)",
                        "extra_attributes": {
                            "associated_devices": {
                                "1": {
                                    "MACAddress": "AA:BB:CC:DD:EE:FF",
                                    "TxBytes": 321,
                                    "RxBytes": 654,
                                    "LastDataDownlinkRate": 1234,
                                    "LastDataUplinkRate": 5678,
                                }
                            }
                        },
                    }
                ]
            },
            config_entry=SimpleNamespace(
                data={"host": "192.168.1.1", "port": 80},
                options={CONF_TRACKING_TIMEOUT: DEFAULT_TRACKING_TIMEOUT},
            ),
            get_parent_device_identifier=lambda _device_key: (DOMAIN, "LIVEBOX"),
            unique_id="LIVEBOX",
        ),
    )
    device = {
        "Key": "AA:BB:CC:DD:EE:FF",
        "Name": "Test device",
        "InterfaceName": "vap5g0priv",
        "DeviceType": "Mobile",
        "Active": True,
        "Tags": "lan edev mac physical wifi flowstats ipv4 ipv6 dhcp events",
        "IPAddress": "10.0.0.10",
        "OperatingFrequencyBand": "5GHz",
        "SignalStrength": -41,
        "SignalNoiseRatio": 32,
        "AvgSignalStrengthByChain": -42,
        "LastDataDownlinkRate": 7777,
        "LastDataUplinkRate": 8888,
    }
    entity = LiveboxDeviceScannerEntity(
        coordinator,
        EntityDescription(key="test_device_tracker", name="Test device"),
        device,
    )

    attrs = cast(dict[str, Any], entity.extra_state_attributes)

    assert attrs["connection"] == "wifi"
    assert attrs["frequency_band"] == "5GHz"
    assert attrs["signal_quality"] == "excellent"
    assert "tx_bytes" not in attrs
    assert "rx_bytes" not in attrs
    assert "last_data_downlink_rate" not in attrs
    assert "last_data_uplink_rate" not in attrs
    assert "signal_strength" not in attrs
