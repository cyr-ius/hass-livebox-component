"""Orange Livebox."""
import logging
from datetime import timedelta

import voluptuous as vol
from aiosysbus.exceptions import LiveboxException
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .bridge import BridgeData
from .const import (
    CALLID,
    CONF_LAN_TRACKING,
    CONF_TRACKING_TIMEOUT,
    COORDINATOR,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    DOMAIN,
    LIVEBOX_API,
    LIVEBOX_ID,
    PLATFORMS,
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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Livebox as config entry."""
    coordinator = LiveboxDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    if (infos := coordinator.data.get("infos")) is None:
        raise PlatformNotReady

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, infos.get("SerialNumber"))},
        manufacturer=infos.get("Manufacturer"),
        name=infos.get("ProductClass"),
        model=infos.get("ModelName"),
        sw_version=infos.get("SoftwareVersion"),
        configuration_url="http://{}:{}".format(
            entry.data.get("host"), entry.data.get("port")
        ),
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    hass.data[DOMAIN][entry.entry_id] = {
        LIVEBOX_ID: entry.unique_id,
        COORDINATOR: coordinator,
        LIVEBOX_API: coordinator.bridge.api,
        CONF_TRACKING_TIMEOUT: entry.options.get(CONF_TRACKING_TIMEOUT, 0),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_remove_cmissed(call) -> None:
        await coordinator.bridge.async_remove_cmissed(call)
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


class LiveboxDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to fetch datas."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry,
    ) -> None:
        """Class to manage fetching data API."""
        self.bridge = BridgeData(hass)
        self.config_entry = config_entry
        self.api = None
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def _async_update_data(self) -> dict:
        """Fetch datas."""
        try:
            lan_tracking = self.config_entry.options.get(CONF_LAN_TRACKING, False)
            self.api = await self.bridge.async_connect(**self.config_entry.data)
            return {
                "cmissed": await self.bridge.async_get_caller_missed(),
                "devices": await self.bridge.async_get_devices(lan_tracking),
                "dsl_status": await self.bridge.async_get_dsl_status(),
                "infos": await self.bridge.async_get_infos(),
                "nmc": await self.bridge.async_get_nmc(),
                "wan_status": await self.bridge.async_get_wan_status(),
                "wifi": await self.bridge.async_get_wifi(),
                "guest_wifi": await self.bridge.async_get_guest_wifi(),
                "count_wired_devices": self.bridge.count_wired_devices,
                "count_wireless_devices": self.bridge.count_wireless_devices,
            }
        except LiveboxException as error:
            raise LiveboxException(error) from error
