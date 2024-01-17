"""Orange Livebox."""
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import device_registry as dr

from .const import CALLID, CONF_USE_TLS, DOMAIN, PLATFORMS
from .coordinator import LiveboxDataUpdateCoordinator

CALLMISSED_SCHEMA = vol.Schema({vol.Optional(CALLID): str})

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Livebox as config entry."""
    hass.data.setdefault(DOMAIN, {})
    scheme = "https" if entry.data.get(CONF_USE_TLS) else "http"

    coordinator = LiveboxDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    if (infos := coordinator.data.get("infos")) is None:
        raise PlatformNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, coordinator.unique_id)},
        manufacturer=infos.get("Manufacturer"),
        name=infos.get("ProductClass", DOMAIN.capitalize()),
        model=infos.get("ModelName"),
        sw_version=infos.get("SoftwareVersion"),
        configuration_url=f"{scheme}://{entry.data.get('host')}:{entry.data.get('port')}",
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_remove_cmissed(call) -> None:
        await coordinator.api.call.get_voiceapplication_clearlist(
            **{CALLID: call.data.get(CALLID)}
        )
        await coordinator.async_refresh()

    hass.services.async_register(
        DOMAIN, "remove_call_missed", async_remove_cmissed, schema=CALLMISSED_SCHEMA
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Reload device tracker if change option."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant,  # pylint: disable=unused-argument
    config_entry: ConfigEntry,  # pylint: disable=unused-argument
    device_entry: dr.DeviceEntry,  # pylint: disable=unused-argument
) -> bool:
    """Remove config entry from a device."""
    return True
