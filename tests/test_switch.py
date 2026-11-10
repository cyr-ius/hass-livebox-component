import copy
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from aiosysbus.exceptions import HttpRequestFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from sqlalchemy import false

from custom_components.livebox.const import CONF_WAN_ACCESS, DOMAIN

ISSUE_191 = "issue_191_repeater_topology_sanitized.json"


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_switch_wifi(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
    service_calls: list[ServiceCall],
):
    """Test that the Wi-Fi switch toggles correctly."""
    # --- Test Setup ---
    # Make a deep copy of the fixture data to allow modification in this test
    wifi_data = copy.deepcopy(await AIOSysbus.nmc.async_get_wifi())

    # Set initial state to OFF for the guest wifi
    wifi_data["status"]["Enable"] = false
    AIOSysbus.nmc.async_get_wifi.return_value = wifi_data

    # This side effect simulates the state change on the Bbox.
    async def mock_set_wireless_guest(enable):
        wifi_data["status"]["Enable"] = bool(enable)

    # Configure the mock to use the side effect
    AIOSysbus.nmc.async_set_wifi.side_effect = mock_set_wireless_guest
    AIOSysbus.nemo.async_wifi.side_effect = mock_set_wireless_guest  # Livebox 5

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # --- Initial State Check ---
    state = hass.states.get(f"switch.{AIOSysbus.__unique_name}_wifi")
    assert state is not None
    assert state.state == STATE_OFF

    # --- Test Turn On ---
    # Simulate a service call to turn the switch on
    data = {
        ATTR_ENTITY_ID: f"switch.{AIOSysbus.__unique_name}_wifi",
    }
    await hass.services.async_call(Platform.SWITCH, "turn_on", data, blocking=True)

    assert len(service_calls) == 1

    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(f"switch.{AIOSysbus.__unique_name}_wifi")
    assert state is not None
    assert state.state == STATE_ON


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_switch_guest_wifi(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
    service_calls: list[ServiceCall],
):
    """Test that the Wi-Fi switch toggles correctly."""
    # --- Test Setup ---
    # Make a deep copy of the fixture data to allow modification in this test
    wifi_data = copy.deepcopy(await AIOSysbus.nmc.async_get_guest_wifi())

    # Set initial state to OFF for the guest wifi
    wifi_data["status"]["Enable"] = false
    AIOSysbus.nmc.async_get_guest_wifi.return_value = wifi_data

    # This side effect simulates the state change on the Bbox.
    async def mock_set_wireless_guest(enable):
        wifi_data["status"]["Enable"] = bool(enable)

    # Configure the mock to use the side effect
    AIOSysbus.nmc.async_set_guest_wifi.side_effect = mock_set_wireless_guest
    AIOSysbus.nmc.async_guest_wifi.side_effect = mock_set_wireless_guest  # Livebox 5

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # --- Initial State Check ---
    state = hass.states.get(f"switch.{AIOSysbus.__unique_name}_guest_wifi")
    assert state is not None
    assert state.state == STATE_OFF

    # --- Test Turn On ---
    # Simulate a service call to turn the switch on
    data = {
        ATTR_ENTITY_ID: f"switch.{AIOSysbus.__unique_name}_guest_wifi",
    }
    await hass.services.async_call(Platform.SWITCH, "turn_on", data, blocking=True)

    assert len(service_calls) == 1

    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(f"switch.{AIOSysbus.__unique_name}_guest_wifi")
    assert state is not None
    assert state.state == STATE_ON


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_switch_wan_access(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
    service_calls: list[ServiceCall],
):
    """Test that the Wi-Fi switch toggles correctly."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # --- Initial State Check ---
    state = hass.states.get("switch.pc_408_wan_access")
    assert state is not None
    assert state.state == STATE_ON

    # --- Test Turn On ---
    # Simulate a service call to turn the switch on
    data = {
        ATTR_ENTITY_ID: "switch.pc_408_wan_access",
    }
    await hass.services.async_call(Platform.SWITCH, "turn_on", data, blocking=True)

    assert len(service_calls) == 1


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_switch_wan_access_override_without_value_disable(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
    service_calls: list[ServiceCall],
):
    """Regression test for #281: WAN access switch flips back ON.

    When override=Disable but value=Enable (the box computed value from
    the weekly schedule doesn't match the manual override), the switch
    must still report OFF. The old code required BOTH override==Disable
    AND value==Disable, which caused the switch to flip back to ON.
    """
    # Mock schedule to return override=Disable but value=Enable (the bug case)
    schedule_data = {
        "data": {
            "scheduleInfo": {
                "base": "Weekly",
                "def": "Enable",
                "ID": "AA:BB:CC:DD:EE:FF",
                "override": "Disable",
                "value": "Enable",
                "enable": True,
                "schedule": [],
            }
        }
    }

    def _mock_get_schedule(*args, **kwargs):
        return schedule_data

    AIOSysbus.schedule.async_get_schedule = AsyncMock(side_effect=_mock_get_schedule)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # The switch must be OFF because override=Disable, regardless of value
    state = hass.states.get("switch.pc_408_wan_access")
    assert state is not None
    assert state.state == STATE_OFF


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_wan_access_switch_unique_id_migration(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """Migration test for issue #287: legacy unique_id without serial prefix.

    Prior to this fix, DeviceWANAccessSwitch stored unique_id = "{mac}_wan_access"
    without the serial-number prefix. The migration in async_setup_entry must
    rename existing entries to "{serial}_{mac}_wan_access" so they are not
    orphaned after upgrade.
    """
    serial = config_entry.unique_id  # "012345678901234" from fixture
    mac = "AA:BB:CC:DD:EE:FF"
    legacy_uid = f"{mac}_wan_access"
    expected_uid = f"{serial}_{legacy_uid}"

    entity_registry = er.async_get(hass)

    # Pre-register an entity with the legacy unique_id (simulates a pre-upgrade entry)
    old_entry = entity_registry.async_get_or_create(
        domain="switch",
        platform="livebox",
        unique_id=legacy_uid,
        config_entry=config_entry,
        suggested_object_id="test_device_wan_access",
    )
    assert old_entry.unique_id == legacy_uid

    # Run integration setup — migration should happen inside async_setup_entry
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # The entity must now carry the new prefixed unique_id
    migrated = entity_registry.async_get(old_entry.entity_id)
    assert migrated is not None
    assert migrated.unique_id == expected_uid

    # No duplicate entry should exist under the old unique_id
    assert entity_registry.async_get_entity_id("switch", "livebox", legacy_uid) is None


@pytest.mark.usefixtures("AIOSysbus")
@pytest.mark.parametrize("api_overlay", [ISSUE_191], indirect=True)
async def test_wan_access_switch_links_device_to_repeater(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """A device created by its WAN access switch ends up linked to its repeater."""
    with patch("custom_components.livebox.PLATFORMS", [Platform.SWITCH]):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    coordinator = config_entry.runtime_data

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    livebox = device_registry.async_get_device_by_identifier(
        (DOMAIN, cast(str, coordinator.unique_id)), config_entry.entry_id
    )
    repeater = device_registry.async_get_device_by_identifier(
        (DOMAIN, "CC:CC:CC:CC:CC:01"), config_entry.entry_id
    )
    client = device_registry.async_get_device_by_identifier(
        (DOMAIN, "DD:DD:DD:DD:DD:01"), config_entry.entry_id
    )
    assert livebox is not None
    assert repeater is not None
    assert client is not None
    assert repeater.via_device_id == livebox.id
    assert client.via_device_id == repeater.id


def _schedule(override: str) -> dict:
    """Return a `Schedule.getSchedule` reply for PC-408."""
    return {
        "data": {
            "scheduleInfo": {
                "base": "Weekly",
                "def": "Enable",
                "ID": "**REDACTED**",
                "override": override,
                "enable": True,
                "schedule": [],
            }
        }
    }


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
@pytest.mark.parametrize(
    ("override", "service", "method", "expected"),
    [
        ("Disable", "turn_on", "async_set_schedule", "Enable"),
        ("Enable", "turn_off", "async_set_schedule", "Disable"),
        (None, "turn_off", "async_add_schedule", "Disable"),
    ],
)
async def test_switch_wan_access_sends_override(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
    override: str | None,
    service: str,
    method: str,
    expected: str,
) -> None:
    """The WAN access switch overrides the schedule, or creates one to lock."""
    AIOSysbus.schedule.async_get_schedule = AsyncMock(
        return_value=_schedule(override) if override else {}
    )
    request = AsyncMock(return_value={"status": True})
    setattr(AIOSysbus.schedule, method, request)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        Platform.SWITCH,
        service,
        {ATTR_ENTITY_ID: "switch.pc_408_wan_access"},
        blocking=True,
    )

    parameters = request.await_args.args[0]
    assert parameters["type"] == "ToD"
    assert (parameters.get("info") or parameters)["override"] == expected


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
@pytest.mark.parametrize(
    ("override", "service", "method", "translation_key"),
    [
        ("Disable", "turn_on", "async_set_schedule", "wan_access_unlock_failed"),
        ("Enable", "turn_off", "async_set_schedule", "wan_access_lock_failed"),
        (None, "turn_off", "async_add_schedule", "wan_access_lock_failed"),
    ],
)
async def test_switch_wan_access_rejected(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
    override: str | None,
    service: str,
    method: str,
    translation_key: str,
) -> None:
    """A schedule change refused by the Livebox raises a translated error."""
    AIOSysbus.schedule.async_get_schedule = AsyncMock(
        return_value=_schedule(override) if override else {}
    )
    setattr(AIOSysbus.schedule, method, AsyncMock(return_value={"status": False}))

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            Platform.SWITCH,
            service,
            {ATTR_ENTITY_ID: "switch.pc_408_wan_access"},
            blocking=True,
        )

    assert err.value.translation_key == translation_key
    assert err.value.translation_placeholders["name"] == "PC-408"


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_switch_communication_error(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """A Livebox error while switching is reported as a translated error."""
    AIOSysbus.nmc.async_set_wifi = AsyncMock(side_effect=HttpRequestFailed("boom"))

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        Platform.SWITCH, DOMAIN, f"{config_entry.unique_id}_wifi"
    )

    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            Platform.SWITCH, "turn_off", {ATTR_ENTITY_ID: entity_id}, blocking=True
        )

    assert err.value.translation_key == "communication_error"
    assert err.value.translation_placeholders == {"error": "boom"}
    assert str(err.value) == "Error while communicating with the Livebox: boom"


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_wan_access_switches_off(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """With the option off, no WAN access switch is created nor schedule polled."""
    hass.config_entries.async_update_entry(
        config_entry, options={**config_entry.options, CONF_WAN_ACCESS: False}
    )

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("switch.pc_408_wan_access") is None
    AIOSysbus.schedule.async_get_schedule.assert_not_called()
    assert config_entry.runtime_data.data["devices_wan_access"] == {}
    # The other switches are still created.
    assert hass.states.async_entity_ids(Platform.SWITCH)


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_wan_access_switches_removed_by_options(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """Turning the option off removes the existing WAN access switches."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    assert entity_registry.async_get("switch.pc_408_wan_access") is not None

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], {**config_entry.options, CONF_WAN_ACCESS: False}
    )
    await hass.async_block_till_done()

    assert entity_registry.async_get("switch.pc_408_wan_access") is None
    assert hass.states.get("switch.pc_408_wan_access") is None
