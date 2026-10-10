"""The tests for the bbox component."""

from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.livebox.const import (
    CONF_DISPLAY_DEVICES,
    CONF_LAN_TRACKING,
    CONF_WIFI_TRACKING,
    DOMAIN,
)
from custom_components.livebox.coordinator import TOPOLOGY_SCAN_INTERVAL


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


@pytest.mark.parametrize("api_overlay", [ISSUE_191], indirect=True)
async def test_device_tracker_follows_client_roaming(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A client moving from a repeater to the Livebox is re-parented (#325)."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = config_entry.runtime_data

    repeater = _device(hass, config_entry, "CC:CC:CC:CC:CC:01")
    assert _device(hass, config_entry, "DD:DD:DD:DD:DD:01").via_device_id == repeater.id

    # The client roams to the Livebox; LastUpdate is left unchanged.
    root = AIOSysbus.topologydiagnostics.async_set_topodiags_build.return_value[
        "status"
    ][0]
    lan = root["Children"][0]
    repeater_vap = lan["Children"][1]["Children"][1]["Children"][0]
    client = repeater_vap["Children"].pop()
    lan["Children"][0]["Children"].append(client)

    freezer.tick(TOPOLOGY_SCAN_INTERVAL)
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    livebox = _device(hass, config_entry, cast(str, coordinator.unique_id))
    assert _device(hass, config_entry, "DD:DD:DD:DD:DD:01").via_device_id == livebox.id


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


ISSUE_350 = "issue_350_apple_private_address_sanitized.json"
# Apple devices using a "Private Wi-Fi Address" are tagged wifi_bridge
# without edev (issue #350). The Watch is even typed "WiFi Bridge".
APPLE_IPHONE = "AA:AA:AA:AA:AA:01"
APPLE_IPAD = "AA:AA:AA:AA:AA:02"
APPLE_WATCH = "AA:AA:AA:AA:AA:03"  # inactive
WINDOWS_PC = "BB:BB:BB:BB:BB:01"  # wifi_bridge too, e.g. virtual switch
WIRED_BRIDGES = {"CC:CC:CC:CC:CC:01", "CC:CC:CC:CC:CC:02"}
ORANGE_REPEATER = "DD:DD:DD:DD:DD:01"  # hnid + ssw, not wifi_bridge
REGULAR_CLIENT = "EE:EE:EE:EE:EE:01"  # edev


@pytest.mark.usefixtures("AIOSysbus")
@pytest.mark.parametrize("AIOSysbus", ["7.1"], indirect=True)
@pytest.mark.parametrize("api_overlay", [ISSUE_350], indirect=True)
@pytest.mark.parametrize(
    ("display_devices", "expected"),
    [
        (
            "All",
            {
                APPLE_IPHONE,
                APPLE_IPAD,
                APPLE_WATCH,
                WINDOWS_PC,
                ORANGE_REPEATER,
                REGULAR_CLIENT,
            },
        ),
        (
            "Active",
            {APPLE_IPHONE, APPLE_IPAD, WINDOWS_PC, ORANGE_REPEATER, REGULAR_CLIENT},
        ),
    ],
)
async def test_device_tracker_tracks_wifi_bridge_clients(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    display_devices: str,
    expected: set[str],
) -> None:
    """Wi-Fi clients tagged wifi_bridge are tracked, wired Wi-Fi bridges are not."""
    # Configuration reported in the issue: wired and wireless tracking enabled.
    hass.config_entries.async_update_entry(
        config_entry,
        options={
            **config_entry.options,
            CONF_DISPLAY_DEVICES: display_devices,
            CONF_LAN_TRACKING: True,
            CONF_WIFI_TRACKING: True,
        },
    )

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    data = config_entry.runtime_data.data
    assert set(data["devices"]) == expected
    assert data["count_wired_devices"] == 0

    entity_registry = er.async_get(hass)
    for key in expected:
        assert entity_registry.async_get_entity_id("device_tracker", DOMAIN, key), key
    for key in WIRED_BRIDGES:
        assert not entity_registry.async_get_entity_id("device_tracker", DOMAIN, key)

    state = hass.states.get("device_tracker.iphone")
    assert state is not None
    assert state.state == STATE_HOME
    assert state.attributes["ip"] == "192.168.1.11"


def _tracker_state(hass: HomeAssistant, key: str) -> State:
    """Return the state of the device tracker of a Livebox device key."""
    entity_id = er.async_get(hass).async_get_entity_id("device_tracker", DOMAIN, key)
    assert entity_id is not None, key
    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    return state


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_device_tracker_reports_ethernet_on_uppercase_interface(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Wired clients on ETH* interfaces (Livebox 6/7) are reported as ethernet."""
    # Fixture keys are redacted, give the PS4 (ETH3) its own key.
    ps4 = AIOSysbus.__devices["status"][67]
    assert ps4["InterfaceName"] == "ETH3"
    ps4["Key"] = "AA:BB:CC:DD:00:67"
    hass.config_entries.async_update_entry(
        config_entry, options={**config_entry.options, CONF_LAN_TRACKING: True}
    )

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    attrs = _tracker_state(hass, "AA:BB:CC:DD:00:67").attributes
    assert attrs["connection"] == "ethernet"
    assert attrs["frequency_band"] == "Wired"


@pytest.mark.usefixtures("AIOSysbus")
@pytest.mark.parametrize("api_overlay", [ISSUE_191], indirect=True)
async def test_device_tracker_keeps_wifi_for_repeater_clients_on_eth(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Wi-Fi clients of a wired repeater stay wifi despite their ETH0 interface."""
    hass.config_entries.async_update_entry(
        config_entry, options={**config_entry.options, CONF_LAN_TRACKING: True}
    )

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    wired = _tracker_state(hass, "BB:BB:BB:BB:BB:01").attributes
    assert wired["connection"] == "ethernet"
    assert wired["frequency_band"] == "Wired"

    repeater_client = _tracker_state(hass, "DD:DD:DD:DD:DD:01").attributes
    assert repeater_client["connection"] == "wifi"
    assert repeater_client["frequency_band"] == "5GHz"


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_device_tracker_new_device_after_empty_start(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Devices are discovered even when the first refresh found none."""
    devices = AIOSysbus.__devices["status"]
    saved = list(devices)
    devices.clear()

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.runtime_data.data["devices"] == {}

    devices.extend(saved)
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("device_tracker.pc_408")
    assert state is not None
    assert hass.states.get("switch.pc_408_wan_access") is not None
