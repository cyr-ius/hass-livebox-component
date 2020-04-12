"""Orange Livebox."""
import asyncio
import logging

from aiosysbus import Sysbus
import voluptuous as vol

from homeassistant import exceptions
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .bridge import BridgeData
from .const import (
    COMPONENTS,
    CONF_LAN_TRACKING,
    DATA_LIVEBOX,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    DOMAIN,
    ID_BOX,
    SESSION_SYSBUS,
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_LAN_TRACKING, default=False): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Load configuration for Livebox component."""
    hass.data.setdefault(DOMAIN, {})

    if not hass.config_entries.async_entries(DOMAIN) and DOMAIN in config:

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=config[DOMAIN]
            )
        )

    return True


async def async_setup_entry(hass, config_entry):
    """Set up Livebox as config entry."""

    session = Sysbus(
        username=config_entry.data["username"],
        password=config_entry.data["password"],
        host=config_entry.data["host"],
        port=config_entry.data["port"],
    )

    perms = await session.async_get_permissions()
    if perms is None:
        return False

    bridge = BridgeData(session, config_entry)
    if bridge is None:
        return False

    hass.data[DOMAIN][config_entry.entry_id] = {
        ID_BOX: config_entry.unique_id,
        DATA_LIVEBOX: bridge,
        SESSION_SYSBUS: session,
    }

    infos = await bridge.async_get_infos()
    if infos is None:
        return False

    _LOGGER.debug(infos)
    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, config_entry.unique_id)},
        manufacturer=infos["Manufacturer"],
        name=infos["ProductClass"],
        model=infos["ModelName"],
        sw_version=infos["SoftwareVersion"],
    )

    for component in COMPONENTS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    async def async_livebox_reboot(call):
        """Handle reboot service call."""
        await session.system.reboot()

    hass.services.async_register(DOMAIN, "reboot", async_livebox_reboot)

    if not config_entry.update_listeners:
        config_entry.add_update_listener(update_listener)

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in COMPONENTS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def update_listener(hass, config_entry):
    """Reload device tracker if change option."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
