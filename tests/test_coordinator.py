"""Tests for the Livebox coordinator."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.livebox.const import CONF_LAN_TRACKING, CONF_WIFI_TRACKING
from custom_components.livebox.coordinator import TOPOLOGY_SCAN_INTERVAL

from .helpers import load_fixture

ISSUE_191 = "issue_191_repeater_topology_sanitized.json"


async def _async_setup(hass: HomeAssistant, config_entry: ConfigEntry) -> Any:
    """Set up the integration and return the coordinator data."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry.runtime_data.data


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_device_counters_match_issue_233_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Test device counts using a sanitized issue #233 diagnostics fixture."""
    fixture = load_fixture("issue_233_livebox_6_diagnostics_sanitized.json")
    query_key = (
        "Devices.async_get_devices::{'expression': {'wifi': "
        "'wifi && (edev || hnid) and .PhysAddress!=\"\"', 'eth': "
        "'eth && (edev || hnid) and .PhysAddress!=\"\"'}}"
    )
    query_response = fixture["data"]["api_raw"][query_key]
    get_devices = AIOSysbus.devices.async_get_devices.side_effect

    def _get_devices(parameters: Any = None) -> dict[str, Any]:
        # Only the tracked-devices query was captured in the issue.
        if parameters and "edev" in parameters["expression"]["eth"]:
            return query_response
        return get_devices(parameters)

    AIOSysbus.devices.async_get_devices.side_effect = _get_devices
    hass.config_entries.async_update_entry(
        config_entry, options={**config_entry.options, CONF_LAN_TRACKING: True}
    )

    data = await _async_setup(hass, config_entry)

    assert data["count_wireless_devices"] == len(query_response["status"]["wifi"])
    assert data["count_wired_devices"] == len(query_response["status"]["eth"])


@pytest.mark.usefixtures("AIOSysbus")
async def test_reboot_log_sorts_sessions_numerically(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    reboot_log: dict[str, Any],
) -> None:
    """Session keys are strings, so "99" must not sort after "134"."""
    reboot_log["NMC.Reboot.Reboot"]["status"]["99"] = {
        "BootDate": "2026-01-01T00:00:00Z",
        "BootReason": "NMC",
        "ShutdownDate": "2026-01-02T00:00:00Z",
        "ShutdownReason": "POR",
    }

    result = (await _async_setup(hass, config_entry))["reboot_log"]

    # Current session is 134; the reason it rebooted comes from session 133.
    assert result["boot_date"] == "2026-09-16T01:08:18Z"
    assert result["shutdown_reason"] == "TR069 reboot"
    assert result["shutdown_date"] == "2026-09-16T01:07:24Z"
    assert result["counters"]["BootCounter"] == 134


@pytest.mark.usefixtures("AIOSysbus")
async def test_reboot_log_handles_single_session(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    reboot_log: dict[str, Any],
) -> None:
    """A gateway with one recorded session has no previous shutdown reason."""
    reboot_log["NMC.Reboot.Reboot"]["status"] = {
        "1": {"BootDate": "2026-09-16T01:08:18Z", "BootReason": "POR"}
    }
    reboot_log["NMC.Reboot"]["status"] = {"BootCounter": 1}

    result = (await _async_setup(hass, config_entry))["reboot_log"]

    assert result["boot_reason"] == "POR"
    assert result["shutdown_reason"] is None


@pytest.mark.usefixtures("AIOSysbus")
@pytest.mark.parametrize(
    ("sessions", "counters"), [({}, {}), ([], None), ("", {"BootCounter": 7})]
)
async def test_reboot_log_survives_unexpected_payloads(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    reboot_log: dict[str, Any],
    sessions: Any,
    counters: Any,
) -> None:
    """Models that do not expose the log must not break the update cycle."""
    reboot_log["NMC.Reboot.Reboot"]["status"] = sessions
    reboot_log["NMC.Reboot"]["status"] = counters

    result = (await _async_setup(hass, config_entry))["reboot_log"]

    assert "boot_date" not in result
    assert isinstance(result["counters"], dict)


@pytest.mark.usefixtures("AIOSysbus")
@pytest.mark.parametrize("api_overlay", [ISSUE_191], indirect=True)
async def test_repeaters_tracked_without_lan_tracking(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Repeaters should stay tracked so clients can attach via_device."""
    data = await _async_setup(hass, config_entry)

    assert data["count_wireless_devices"] == 4
    assert data["count_wired_devices"] == 0
    assert "CC:CC:CC:CC:CC:01" in data["devices"]
    assert "BB:BB:BB:BB:BB:01" not in data["devices"]


@pytest.mark.usefixtures("AIOSysbus")
@pytest.mark.parametrize("api_overlay", [ISSUE_191], indirect=True)
async def test_repeaters_skipped_when_tracking_disabled(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """When both tracking modes are off, no device trackers should be created."""
    hass.config_entries.async_update_entry(
        config_entry,
        options={
            **config_entry.options,
            CONF_LAN_TRACKING: False,
            CONF_WIFI_TRACKING: False,
        },
    )

    data = await _async_setup(hass, config_entry)

    assert data["devices"] == {}
    assert data["count_wireless_devices"] == 0
    assert data["count_wired_devices"] == 0


@pytest.mark.parametrize("api_overlay", [ISSUE_191], indirect=True)
async def test_topology_kept_on_invalid_status(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Malformed topology status should fall back to the existing cache."""
    data = await _async_setup(hass, config_entry)
    via_device = data["topology_via_device"]
    repeaters = data["topology_repeaters"]
    assert repeaters == {"CC:CC:CC:CC:CC:01": "Repeater-1"}

    topology = AIOSysbus.topologydiagnostics
    topology.async_get_topodiags.return_value = {"status": []}
    topology.async_set_topodiags_build.reset_mock()
    coordinator = config_entry.runtime_data
    freezer.tick(TOPOLOGY_SCAN_INTERVAL)
    await coordinator.async_refresh()

    assert coordinator.data["topology_via_device"] == via_device
    assert coordinator.data["topology_repeaters"] == repeaters
    topology.async_set_topodiags_build.assert_not_awaited()


@pytest.mark.parametrize("api_overlay", [ISSUE_191], indirect=True)
async def test_topology_rebuilt_after_scan_interval(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Topology is cached, then rebuilt even when LastUpdate is unchanged."""
    await _async_setup(hass, config_entry)
    build = AIOSysbus.topologydiagnostics.async_set_topodiags_build
    build.reset_mock()
    coordinator = config_entry.runtime_data

    await coordinator.async_refresh()
    build.assert_not_awaited()

    freezer.tick(TOPOLOGY_SCAN_INTERVAL)
    await coordinator.async_refresh()
    build.assert_awaited_once()


async def test_stats_keep_interfaces_without_traffic(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Interfaces without traffic should still produce zeroed stats."""
    AIOSysbus.homelan.async_get_interface.return_value = {
        "status": {
            "eth0": {"Name": "ETH0", "FriendlyName": "eth0"},
            "eth1": {"Name": "ETH1", "FriendlyName": "eth1"},
        }
    }
    AIOSysbus.homelan.async_get_results.return_value = {
        "status": {
            "eth0": {"Traffic": []},
            "eth1": {"Traffic": [{"Rx_Counter": 3_000_000, "Tx_Counter": 6_000_000}]},
        }
    }

    stats = (await _async_setup(hass, config_entry))["stats"]

    assert stats["ETH0"]["rate_rx"] == 0.0
    assert stats["ETH0"]["rate_tx"] == 0.0
    assert stats["ETH1"]["rate_rx"] == 0.1
    assert stats["ETH1"]["rate_tx"] == 0.2
