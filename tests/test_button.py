"""The tests for the bbox component."""

from typing import Generator
from unittest.mock import AsyncMock, MagicMock

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant


async def test_button(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: Generator[AsyncMock | MagicMock],
) -> None:
    """Test reboot button."""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    data = {
        ATTR_ENTITY_ID: "button.livebox_7_livebox_restart",
    }

    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        service_data=data,
        blocking=True,
    )
    await hass.async_block_till_done()

    data = {
        ATTR_ENTITY_ID: "button.livebox_7_livebox_ring",
    }

    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        service_data=data,
        blocking=True,
    )
    await hass.async_block_till_done()
