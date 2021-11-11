"""Orange Livebox."""
import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .bridge import BridgeData
from .const import (
    CALLID,
    PLATFORMS,
    CONF_LAN_TRACKING,
    CONF_TRACKING_TIMEOUT,
    COORDINATOR,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    DOMAIN,
    LIVEBOX_API,
    LIVEBOX_ID,
    UNSUB_LISTENER,
)

CALLMISSED_SCHEMA = vol.Schema({vol.Optional(CALLID): str})

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

SCAN_INTERVAL = timedelta(minutes=1)

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
    try:
        await bridge.async_connect()
    except Exception:  # pylint: disable=broad-except
        return False

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=bridge.async_fetch_datas,
        update_interval=SCAN_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()

    if (infos := coordinator.data.get("infos")) is None:
        raise PlatformNotReady

    unsub_listener = config_entry.add_update_listener(update_listener)

    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, infos.get("SerialNumber"))},
        manufacturer=infos.get("Manufacturer"),
        name=infos.get("ProductClass"),
        model=infos.get("ModelName"),
        sw_version=infos.get("SoftwareVersion"),
    )

    hass.data[DOMAIN][config_entry.entry_id] = {
        LIVEBOX_ID: config_entry.unique_id,
        UNSUB_LISTENER: unsub_listener,
        COORDINATOR: coordinator,
        LIVEBOX_API: bridge.api,
        CONF_TRACKING_TIMEOUT: config_entry.options.get(CONF_TRACKING_TIMEOUT, 0),
    }

    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)

    async def async_box_restart(call) -> None:  # pylint: disable=unused-argument
        """Handle restart service call."""
        await bridge.async_reboot()

    hass.services.async_register(
        DOMAIN, "reboot", async_box_restart, schema=vol.Schema({})
    )

    async def async_remove_cmissed(call) -> None:
        await bridge.async_remove_cmissed(call)
        await coordinator.async_refresh()

    hass.services.async_register(
        DOMAIN, "remove_call_missed", async_remove_cmissed, schema=CALLMISSED_SCHEMA
    )

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    hass.data[DOMAIN][config_entry.entry_id][UNSUB_LISTENER]()
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def update_listener(hass, config_entry):
    """Reload device tracker if change option."""
    await hass.config_entries.async_reload(config_entry.entry_id)
