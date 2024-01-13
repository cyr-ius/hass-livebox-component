"""Corddinator for Livebox."""
from __future__ import annotations

import logging
from datetime import timedelta

from aiosysbus.exceptions import LiveboxException
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .bridge import BridgeData
from .const import CONF_LAN_TRACKING, DOMAIN

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
            devices = await self.bridge.async_get_devices(lan_tracking)
            return {
                "cmissed": await self.bridge.async_get_caller_missed(),
                "devices": devices,
                "dsl_status": await self.bridge.async_get_dsl_status(),
                "infos": await self.bridge.async_get_infos(),
                "nmc": await self.bridge.async_get_nmc(),
                "wan_status": await self.bridge.async_get_wan_status(),
                "wifi": await self.bridge.async_get_wifi(),
                "guest_wifi": await self.bridge.async_get_guest_wifi(),
                "count_wired_devices": self.bridge.count_wired_devices,
                "count_wireless_devices": self.bridge.count_wireless_devices,
                "devices_wan_access": {
                    device_key: await self.bridge.async_get_device_schedule(device_key)
                    for device_key in devices
                },
            }
        except LiveboxException as error:
            raise LiveboxException(error) from error
