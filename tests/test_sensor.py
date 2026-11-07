"""Tests for the Bbox sensor platform."""

from typing import Any
from unittest.mock import AsyncMock

import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfDataRate, UnitOfInformation
from homeassistant.core import HomeAssistant, State

from custom_components.livebox.const import CONF_LAN_TRACKING, DOMAIN
from custom_components.livebox.sensor import SENSOR_TYPES

from .helpers import load_fixture, object_not_found


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_sensors_state(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
):
    """Test the state of various sensors."""
    # Setup the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # The Livebox 3 optical termination is an external box: nothing to read.
    has_ont = AIOSysbus.__model != "3"
    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_power_tx")
    assert (state is not None) is has_ont
    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_power_rx")
    assert (state is not None) is has_ont

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_tx")
    assert state is not None
    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_rx")
    assert state is not None

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_callers")
    assert state is not None

    if AIOSysbus.__model in ["7"]:
        state = er.async_get(hass).async_get("sensor.pc_408_downlink_rate")
        assert state is not None
        state = er.async_get(hass).async_get("sensor.pc_408_uplink_rate")
        assert state is not None

    if AIOSysbus.__model in ["7.1"]:
        state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_eth2_rate_rx")
        assert state is not None
        assert float(state.state) >= 0
        state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_eth2_rate_tx")
        assert state is not None
        assert float(state.state) >= 0

    # entity_registry_enabled_default=False
    state = er.async_get(hass).async_get(f"sensor.{AIOSysbus.__unique_name}_wifi_tx")
    assert state is not None
    state = er.async_get(hass).async_get(f"sensor.{AIOSysbus.__unique_name}_wifi_rx")
    assert state is not None
    state = er.async_get(hass).async_get(
        f"sensor.{AIOSysbus.__unique_name}_ports_forwarding"
    )
    assert state is not None
    state = er.async_get(hass).async_get(
        f"sensor.{AIOSysbus.__unique_name}_dhcp_leases"
    )
    assert state is not None
    state = er.async_get(hass).async_get(
        f"sensor.{AIOSysbus.__unique_name}_guest_dhcp_leases"
    )
    assert state is not None


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_last_reboot_reason_sensor(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
):
    """The reason comes from the previous session, the dates from the current one."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_last_reboot_reason")
    assert state is not None
    assert state.state == "TR069 reboot"
    assert state.attributes["Boot date"] == "2026-09-16T01:08:18Z"
    assert state.attributes["Boot reason"] == "NMC"
    assert state.attributes["Shutdown date"] == "2026-09-16T01:07:24Z"
    assert state.attributes["Boot counter"] == 134
    assert state.attributes["Watchdog reboot counter"] == 3
    assert state.attributes["Reboots since last upgrade"] == 85


@pytest.mark.parametrize("AIOSysbus", ["3"], indirect=True)
async def test_last_reboot_reason_sensor_absent_without_reboot_log(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
    reboot_log: dict[str, Any],
) -> None:
    """A gateway without `NMC.Reboot` gets no permanently unknown sensor (#361)."""
    reboot_log["NMC.Reboot.Reboot"] = object_not_found("NMC.Reboot.Reboot")
    reboot_log["NMC.Reboot"] = object_not_found("NMC.Reboot")

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert (
        hass.states.get(f"sensor.{AIOSysbus.__unique_name}_last_reboot_reason") is None
    )
    assert hass.states.get(f"sensor.{AIOSysbus.__unique_name}_callers") is not None


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_fiber_power_unknown_without_reading(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """A missing optical reading is unknown, not a misleading 0 dBm (#362)."""
    get_mibs = AIOSysbus.nemo.async_get_MIBs.side_effect

    def _get_mibs(intf: str, *args: Any) -> dict[str, Any]:
        # Fiber link down: the gpon MIB comes back without any reading.
        if intf == "veip0":
            return {"status": {"gpon": {"veip0": {"ONUState": "O1"}}}}
        return get_mibs(intf, *args)

    AIOSysbus.nemo.async_get_MIBs.side_effect = _get_mibs

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    for key in ("fiber_power_rx", "fiber_power_tx"):
        state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_{key}")
        assert state is not None
        assert state.state == "unknown"


@pytest.mark.parametrize("AIOSysbus", ["7", "7.1", "7.2"], indirect=True)
async def test_rate_sensors_match_issue_258_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """Test dynamic rate sensors keep distinct values from issue #258."""
    fixture = load_fixture("issue_258_livebox_nautilus_diagnostics_sanitized.json")
    stats = fixture["data"]["data"]["stats"]
    # The issue only provides the computed rates: rebuild the HomeLan
    # counters (bits over 30 seconds) the coordinator derives them from.
    AIOSysbus.homelan.async_get_interface.return_value = {
        "status": {
            item["friendly_name"]: {"Name": name, "FriendlyName": item["friendly_name"]}
            for name, item in stats.items()
        }
    }
    AIOSysbus.homelan.async_get_results.return_value = {
        "status": {
            item["friendly_name"]: {
                "Traffic": [
                    {
                        "Rx_Counter": item["rate_rx"] * 30_000_000,
                        "Tx_Counter": item["rate_tx"] * 30_000_000,
                    }
                ]
            }
            for item in stats.values()
        }
    }

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    unique_id = config_entry.runtime_data.unique_id

    def _value(key: str) -> float:
        entity_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{unique_id}_{key}"
        )
        assert entity_id is not None, key
        state = hass.states.get(entity_id)
        assert state is not None, key
        return float(state.state)

    assert _value("vap5g0priv_rate_rx") == 0.01
    assert _value("vap5g0priv_rate_tx") == 0.06
    assert _value("ETH0_rate_rx") == 0.01
    assert _value("ETH0_rate_tx") == 0.0


@pytest.mark.parametrize("AIOSysbus", ["7.1"], indirect=True)
async def test_rate_sensors_use_megabits_per_second_math(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """Test rate sensors use Mbit/s math to match their declared unit."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    rx_state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_eth2_rate_rx")
    assert rx_state is not None
    assert float(rx_state.state) == 0.01

    tx_state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_eth2_rate_tx")
    assert tx_state is not None
    assert float(tx_state.state) == 5.69


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_device_metric_sensors_are_created_for_wifi_clients(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """Test per-device Wi-Fi sensors expose the expected metrics."""
    AIOSysbus.__devices["status"].append(
        {
            "Key": "AA:BB:CC:DD:EE:FF",
            "Name": "Test device",
            "PhysAddress": "AA:BB:CC:DD:EE:FF",
            "Active": True,
            "Tags": "lan edev mac physical wifi ipv4 ipv6 dhcp events",
            "InterfaceName": "vap5g0priv0",
            "SignalStrength": -41,
            "SignalNoiseRatio": 32,
            "LastDataDownlinkRate": 7777,
            "LastDataUplinkRate": 8888,
        }
    )
    wlanvap = AIOSysbus.api_raw["NeMo.async_get_MIBs::lan"]["status"]["wlanvap"]
    wlanvap["vap5g0priv0"]["AssociatedDevice"]["AA:BB:CC:DD:EE:FF"] = {
        "MACAddress": "AA:BB:CC:DD:EE:FF",
        "TxBytes": 321,
        "RxBytes": 654,
    }

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    def _state(key: str) -> State:
        entity_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{config_entry.runtime_data.unique_id}_{key}"
        )
        assert entity_id is not None, key
        state = hass.states.get(entity_id)
        assert state is not None, key
        return state

    downlink = _state("aa_bb_cc_dd_ee_ff_downlink_rate")
    assert float(downlink.state) == 7.777
    assert downlink.attributes["unit_of_measurement"] == (
        UnitOfDataRate.MEGABITS_PER_SECOND
    )
    assert float(_state("aa_bb_cc_dd_ee_ff_uplink_rate").state) == 8.888
    tx_bytes = _state("aa_bb_cc_dd_ee_ff_tx_bytes")
    assert float(tx_bytes.state) == 0.000321
    assert tx_bytes.attributes["unit_of_measurement"] == UnitOfInformation.MEGABYTES
    assert float(_state("aa_bb_cc_dd_ee_ff_rx_bytes").state) == 0.000654
    assert float(_state("aa_bb_cc_dd_ee_ff_signal_strength").state) == -41
    assert float(_state("aa_bb_cc_dd_ee_ff_signal_noise_ratio").state) == 32
    assert downlink.attributes["friendly_name"] == "Test device Downlink Rate"

    entry = entity_registry.async_get(downlink.entity_id)
    assert entry is not None and entry.device_id is not None
    device = device_registry.async_get(entry.device_id)
    assert device is not None
    assert device.identifiers == {(DOMAIN, "AA:BB:CC:DD:EE:FF")}


def test_fiber_rate_attributes_use_gigabits_per_second() -> None:
    """Fiber status rate attributes should match their Gbit/s labels."""
    data = {
        "fiber_status": {
            "DownstreamMaxRate": 2488320,
            "DownstreamCurrRate": 2488320,
            "UpstreamMaxRate": 1244160,
            "UpstreamCurrRate": 1244160,
            "MaxBitRateSupported": 10000,
        }
    }

    rx_description = next(
        description
        for description in SENSOR_TYPES
        if description.key == "fiber_power_rx"
    )
    tx_description = next(
        description
        for description in SENSOR_TYPES
        if description.key == "fiber_power_tx"
    )

    assert rx_description.attrs is not None
    assert tx_description.attrs is not None
    assert rx_description.attrs["Downstream max rate Gbps"](data) == 2.48832
    assert rx_description.attrs["Downstream current rate Gbps"](data) == 2.48832
    assert rx_description.attrs["Max bitrate (Gbps)"](data) == 10
    assert tx_description.attrs["Upstream max rate (Gbps)"](data) == 1.24416
    assert tx_description.attrs["Upstream current rate (Gbps)"](data) == 1.24416
    assert tx_description.attrs["Max bitrate (Gbps)"](data) == 10


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_rolling_counter_state_not_shared_across_setups(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """A reloaded entry starts its 32-bit counters from scratch."""
    wifi_stats = AIOSysbus.api_raw["Nmc.async_get_wifi_stats"]["data"]
    entity_id = f"sensor.{AIOSysbus.__unique_name}_wifi_rx"

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id) is not None

    wifi_stats["RxBytes"] = 1_000_000
    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    # 1 MB, not 4 GiB + 1 MB from a rollover against the previous entry.
    assert float(hass.states.get(entity_id).state) == 1


@pytest.mark.parametrize(
    "api_overlay", ["issue_347_funbox6_sanitized.json"], indirect=True
)
@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_funbox6_fiber_sensors(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """A Funbox 6 reads traffic on ETH0 and hides unsupported optics (#347)."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    AIOSysbus.nemo.async_get_net_dev_stats.assert_any_call("ETH0")
    assert ("veip0",) not in [
        call.args for call in AIOSysbus.nemo.async_get_net_dev_stats.call_args_list
    ]

    unique_name = AIOSysbus.__unique_name
    state = hass.states.get(f"sensor.{unique_name}_fiber_rx")
    assert state is not None
    assert float(state.state) == pytest.approx(98.742267559)

    # SignalRxPower is 0 on this gateway: unknown, not a perfect 0 dBm.
    state = hass.states.get(f"sensor.{unique_name}_fiber_power_rx")
    assert state is not None
    assert state.state == "unknown"

    state = hass.states.get(f"sensor.{unique_name}_fiber_power_tx")
    assert state is not None
    assert float(state.state) == -8.42
    # Mixed-case `OnuState` key and voltage in units of 100 uV.
    assert state.attributes["ONU State"] == "O1_Initial"
    assert state.attributes["Voltage (V)"] == 3.2616
    # Readings this gateway leaves at 0 are not reported.
    assert state.attributes["Bias (mA)"] is None
    assert state.attributes["Upstream max rate (Gbps)"] is None
    assert state.attributes["Upstream current rate (Gbps)"] is None
    rx_state = hass.states.get(f"sensor.{unique_name}_fiber_power_rx")
    assert rx_state is not None
    assert rx_state.attributes["Downstream max rate Gbps"] is None
    assert rx_state.attributes["Downstream current rate Gbps"] is None


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_fiber_onu_state_upper_case_key(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """The ONU state is read from the upper-case `ONUState` key too."""
    gpon = AIOSysbus.api_raw["NeMo.async_get_MIBs::veip0"]["status"]["gpon"]["veip0"]
    gpon["ONUState"] = gpon.pop("OnuState")

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_power_rx")
    assert state is not None
    assert state.attributes["ONU State"] == "O5_Operation"


REPEATER_WIRED_PC = "AA:AA:AA:AA:AA:01"


@pytest.mark.usefixtures("AIOSysbus", "entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    "api_overlay",
    ["issue_326_wired_behind_wifi_repeater_sanitized.json"],
    indirect=True,
)
async def test_device_metric_sensors_skip_wired_clients_of_wifi_repeater(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Wired clients on a repeater vap backhaul get no Wi-Fi metric sensors."""
    hass.config_entries.async_update_entry(
        config_entry, options={**config_entry.options, CONF_LAN_TRACKING: True}
    )
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert REPEATER_WIRED_PC in config_entry.runtime_data.data["devices"]
    entity_registry = er.async_get(hass)
    unique_id = config_entry.runtime_data.unique_id
    assert not entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{unique_id}_aa_aa_aa_aa_aa_01_signal_strength"
    )
    assert entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{unique_id}_bb_bb_bb_bb_bb_01_signal_strength"
    )
