"""Tests for the Bbox sensor platform."""

from typing import Any, cast
from unittest.mock import AsyncMock

import homeassistant.helpers.entity_registry as er
import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytest_homeassistant_custom_component.common import load_json_object_fixture

from custom_components.livebox.coordinator import LiveboxDataUpdateCoordinator
from custom_components.livebox.sensor import LiveboxSensor, async_setup_entry


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
