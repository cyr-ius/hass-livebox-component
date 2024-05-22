"""Orange Livebox."""

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CALLID, DOMAIN, PLATFORMS
from .coordinator import LiveboxDataUpdateCoordinator

type LiveboxConfigEntry = ConfigEntry[LiveboxDataUpdateCoordinator]

CALLMISSED_SCHEMA = vol.Schema({vol.Optional(CALLID): str})

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: LiveboxConfigEntry) -> bool:
    """Set up Livebox as config entry."""
    coordinator = LiveboxDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_remove_cmissed(call) -> None:
        await coordinator.api.voiceservice.async_clear_calllist(
            {CALLID: call.data.get(CALLID)}
        )
        await coordinator.async_refresh()

    hass.services.async_register(
        DOMAIN, "remove_call_missed", async_remove_cmissed, schema=CALLMISSED_SCHEMA
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: LiveboxConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: LiveboxConfigEntry):
    """Reload device tracker if change option."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant,  # pylint: disable=unused-argument
    config_entry: ConfigEntry,  # pylint: disable=unused-argument
    device_entry: dr.DeviceEntry,  # pylint: disable=unused-argument
) -> bool:
    """Remove config entry from a device."""
    return True
