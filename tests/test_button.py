"""The tests for the bbox component."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiosysbus.exceptions import HttpRequestFailed
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_button(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
    service_calls: list[ServiceCall],
) -> None:
    """Test reboot button."""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    data = {
        ATTR_ENTITY_ID: f"button.{AIOSysbus.__unique_name}_livebox_restart",
    }

    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, service_data=data, blocking=True
    )
    await hass.async_block_till_done()
    assert len(service_calls) == 1

    data = {
        ATTR_ENTITY_ID: f"button.{AIOSysbus.__unique_name}_ring_your_phone",
    }

    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        service_data=data,
        blocking=True,
    )
    await hass.async_block_till_done()
    assert len(service_calls) == 2


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_button_communication_error(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """A Livebox error on press is reported as a translated error."""
    AIOSysbus.nmc.async_reboot = AsyncMock(side_effect=HttpRequestFailed("boom"))

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: f"button.{AIOSysbus.__unique_name}_livebox_restart"},
            blocking=True,
        )

    assert err.value.translation_key == "communication_error"
