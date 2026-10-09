"""The tests for the bbox component."""

from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.livebox.const import DOMAIN


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_device_tracker(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Test the device tracker platform."""
    # Fixture keys are redacted, give PC-408 its own key so it is not merged.
    AIOSysbus.__devices["status"][69]["Key"] = "AA:BB:CC:DD:04:08"
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


ISSUE_191 = "issue_191_repeater_topology_sanitized.json"


def _device(hass: HomeAssistant, entry: ConfigEntry, key: str) -> dr.DeviceEntry:
    """Return the registry device of a Livebox device key."""
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, key), entry.entry_id
    )
    assert device is not None, key
    return device


@pytest.mark.usefixtures("AIOSysbus")
@pytest.mark.parametrize("api_overlay", [ISSUE_191], indirect=True)
async def test_device_tracker_links_clients_to_repeaters(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Repeaters are registered before their clients so via_device resolves."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data
    livebox = _device(hass, config_entry, cast(str, coordinator.unique_id))
    repeater = _device(hass, config_entry, "CC:CC:CC:CC:CC:01")

    assert repeater.via_device_id == livebox.id
    assert _device(hass, config_entry, "DD:DD:DD:DD:DD:01").via_device_id == repeater.id
    assert _device(hass, config_entry, "AA:AA:AA:AA:AA:01").via_device_id == livebox.id


@pytest.mark.parametrize("api_overlay", [ISSUE_191], indirect=True)
async def test_device_tracker_updates_via_device_on_coordinator_refresh(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Re-parent an existing tracker when topology appears on a later refresh."""
    topology = AIOSysbus.topologydiagnostics.async_set_topodiags_build
    topology_response = topology.return_value
    topology.return_value = {"status": []}

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = config_entry.runtime_data

    livebox = _device(hass, config_entry, cast(str, coordinator.unique_id))
    assert _device(hass, config_entry, "DD:DD:DD:DD:DD:01").via_device_id == livebox.id

    topology.return_value = topology_response
    client = next(
        device
        for device in AIOSysbus.__devices["status"]
        if device["Key"] == "DD:DD:DD:DD:DD:01"
    )
    client["IPAddress"] = "192.168.1.99"
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    repeater = _device(hass, config_entry, "CC:CC:CC:CC:CC:01")
    assert _device(hass, config_entry, "DD:DD:DD:DD:DD:01").via_device_id == repeater.id
    state = hass.states.get("device_tracker.device_repeater_5g_1")
    assert state is not None
    assert state.attributes["ip"] == "192.168.1.99"


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_device_tracker_adds_associated_wifi_stats(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Wi-Fi device trackers should keep only contextual attributes."""
    AIOSysbus.__devices["status"].append(
        {
            "Key": "AA:BB:CC:DD:EE:FF",
            "Name": "Test device",
            "PhysAddress": "AA:BB:CC:DD:EE:FF",
            "InterfaceName": "vap5g0priv0",
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
    )
    wlanvap = AIOSysbus.api_raw["NeMo.async_get_MIBs::lan"]["status"]["wlanvap"]
    wlanvap["vap5g0priv0"]["AssociatedDevice"]["AA:BB:CC:DD:EE:FF"] = {
        "MACAddress": "AA:BB:CC:DD:EE:FF",
        "TxBytes": 321,
        "RxBytes": 654,
        "LastDataDownlinkRate": 1234,
        "LastDataUplinkRate": 5678,
    }

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("device_tracker.test_device")
    assert state is not None
    attrs = state.attributes
    assert attrs["connection"] == "wifi"
    assert attrs["frequency_band"] == "5GHz"
    assert attrs["signal_quality"] == "excellent"
    assert "tx_bytes" not in attrs
    assert "rx_bytes" not in attrs
    assert "last_data_downlink_rate" not in attrs
    assert "last_data_uplink_rate" not in attrs
    assert "signal_strength" not in attrs
