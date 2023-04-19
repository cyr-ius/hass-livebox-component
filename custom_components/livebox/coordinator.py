"""Corddinator for Livebox."""
from __future__ import annotations

from datetime import timedelta
import logging

from aiosysbus.exceptions import LiveboxException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .bridge import BridgeData
from .const import DOMAIN, CONF_LAN_TRACKING

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=1)


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
