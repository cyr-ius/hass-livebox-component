"""Tests for the Bbox sensor platform."""

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import homeassistant.helpers.entity_registry as er
import pytest
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfDataRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytest_homeassistant_custom_component.common import load_json_object_fixture

from custom_components.livebox.coordinator import LiveboxDataUpdateCoordinator
from custom_components.livebox.sensor import (
    SENSOR_TYPES,
    LiveboxSensor,
    async_setup_entry,
)


def _load_fixture(name: str) -> dict[str, Any]:
    """Load a typed test fixture."""
    return cast(dict[str, Any], load_json_object_fixture(name))


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

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_power_tx")
    assert state is not None
    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_power_rx")
    assert state is not None

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


async def test_rate_sensors_match_issue_258_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Test dynamic rate sensors keep distinct values from issue #258."""
    fixture = _load_fixture("issue_258_livebox_nautilus_diagnostics_sanitized.json")

    coordinator = LiveboxDataUpdateCoordinator(hass, config_entry)
    coordinator.unique_id = "issue258"
    coordinator.data = fixture["data"]["data"]
    config_entry.runtime_data = coordinator

    entities: list[LiveboxSensor] = []

    def _add_entities(
        new_entities: list[LiveboxSensor], update_before_add: bool = False
    ) -> None:
        del update_before_add
        entities.extend(new_entities)

    await async_setup_entry(
        hass, config_entry, cast(AddEntitiesCallback, _add_entities)
    )

    sensors = {entity.entity_description.key: entity for entity in entities}

    assert sensors["vap5g0priv_rate_rx"].native_value == 0.01
    assert sensors["vap5g0priv_rate_tx"].native_value == 0.06
    assert sensors["ETH0_rate_rx"].native_value == 0.01
    assert sensors["ETH0_rate_tx"].native_value == 0.0


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
    assert float(rx_state.state) == 0.09

    tx_state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_eth2_rate_tx")
    assert tx_state is not None
    assert float(tx_state.state) == 45.48


async def test_device_metric_sensors_are_created_for_wifi_clients(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Test per-device Wi-Fi sensors expose the expected metrics."""
    coordinator = cast(
        LiveboxDataUpdateCoordinator,
        SimpleNamespace(
            unique_id="LIVEBOX",
            config_entry=SimpleNamespace(
                data={"host": "192.168.1.1", "port": 80},
                options={},
            ),
            signal_device_new="livebox-LIVEBOX-device-new",
            get_parent_device_identifier=lambda _device_key: ("livebox", "LIVEBOX"),
            data={
                "devices": {
                    "AA:BB:CC:DD:EE:FF": {
                        "Key": "AA:BB:CC:DD:EE:FF",
                        "Name": "Test device",
                        "InterfaceName": "vap5g0priv",
                        "SignalStrength": -41,
                        "SignalNoiseRatio": 32,
                        "LastDataDownlinkRate": 7777,
                        "LastDataUplinkRate": 8888,
                    }
                },
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
                                }
                            }
                        },
                    }
                ],
            },
        ),
    )
    config_entry.runtime_data = coordinator

    entities: list[LiveboxSensor] = []

    def _add_entities(
        new_entities: list[LiveboxSensor], update_before_add: bool = False
    ) -> None:
        del update_before_add
        entities.extend(new_entities)

    await async_setup_entry(
        hass, config_entry, cast(AddEntitiesCallback, _add_entities)
    )

    sensors = {entity.entity_description.key: entity for entity in entities}

    assert sensors["aa_bb_cc_dd_ee_ff_downlink_rate"].native_value == 7777000
    assert sensors["aa_bb_cc_dd_ee_ff_uplink_rate"].native_value == 8888000
    downlink_description = cast(
        SensorEntityDescription,
        sensors["aa_bb_cc_dd_ee_ff_downlink_rate"].entity_description,
    )
    assert (
        downlink_description.native_unit_of_measurement
        == UnitOfDataRate.BITS_PER_SECOND
    )
    assert (
        downlink_description.suggested_unit_of_measurement
        == UnitOfDataRate.MEGABITS_PER_SECOND
    )
    assert sensors["aa_bb_cc_dd_ee_ff_tx_bytes"].native_value == 321
    assert sensors["aa_bb_cc_dd_ee_ff_rx_bytes"].native_value == 654
    assert sensors["aa_bb_cc_dd_ee_ff_signal_strength"].native_value == -41
    assert sensors["aa_bb_cc_dd_ee_ff_signal_noise_ratio"].native_value == 32
    assert sensors["aa_bb_cc_dd_ee_ff_downlink_rate"].extra_state_attributes is None
    assert sensors["aa_bb_cc_dd_ee_ff_uplink_rate"].extra_state_attributes is None
    assert sensors["aa_bb_cc_dd_ee_ff_tx_bytes"].extra_state_attributes is None
    assert sensors["aa_bb_cc_dd_ee_ff_rx_bytes"].extra_state_attributes is None
    assert sensors["aa_bb_cc_dd_ee_ff_downlink_rate"].name == "Downlink Rate"
    assert sensors["aa_bb_cc_dd_ee_ff_downlink_rate"].device_info is not None
    assert sensors["aa_bb_cc_dd_ee_ff_downlink_rate"].device_info["identifiers"] == {
        ("livebox", "AA:BB:CC:DD:EE:FF")
    }


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
