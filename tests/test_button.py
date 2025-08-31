"""The tests for the bbox component."""

from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall


@pytest.mark.parametrize("AIOSysbus", ["5", "7", "7.1"], indirect=True)
async def test_button(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: Generator[AsyncMock | MagicMock],
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
