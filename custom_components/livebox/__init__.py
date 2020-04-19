"""Orange Livebox."""
import asyncio
import logging
import voluptuous as vol

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

    bridge = BridgeData(hass, config_entry)
    await bridge.async_connect(config_entry.data)
    if bridge is None:
        return False

    hass.data[DOMAIN][config_entry.entry_id] = {
        ID_BOX: config_entry.unique_id,
        DATA_LIVEBOX: bridge,
    }

    infos = await bridge.async_get_infos()
    if infos is None:
        return False

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
        await bridge.async_reboot()

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
