"""Coordinator for Livebox."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from aiosysbus import AIOSysbus
from aiosysbus.exceptions import AiosysbusException, AuthenticationFailed

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import DEFAULT_TIME_ZONE, UTC

from .const import CONF_LAN_TRACKING, DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=1)


class LiveboxDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to fetch datas."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Class to manage fetching data API."""
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.config_entry = config_entry
        self.api = AIOSysbus(
            username=config_entry.data["username"],
            password=config_entry.data["password"],
            session=async_create_clientsession(hass),
            host=config_entry.data["host"],
            port=config_entry.data["port"],
            use_tls=config_entry.data.get("use_tls", False),
        )
        self.unique_id: str | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch datas."""
        try:
            await self.api.async_connect()
            lan_tracking = self.config_entry.options.get(CONF_LAN_TRACKING, False)
            devices, device_counters = await self.async_get_devices(lan_tracking)
            infos = await self.async_get_infos()
            self.unique_id = infos["SerialNumber"]
            return {
                "cmissed": await self.async_get_caller_missed(),
                "devices": devices,
                "dsl_status": await self.async_get_dsl_status(),
                "infos": infos,
                "nmc": await self.async_get_nmc(),
                "wan_status": await self.async_get_wan_status(),
                "wifi": await self.async_get_wifi(),
                "guest_wifi": await self.async_get_guest_wifi(),
                "count_wired_devices": device_counters["wired"],
                "count_wireless_devices": device_counters["wireless"],
                "devices_wan_access": {
                    key: await self.async_get_device_schedule(key) for key in devices
                },
            }
        except AuthenticationFailed as error:
            raise ConfigEntryAuthFailed from error
        except AiosysbusException as error:
            raise UpdateFailed(error) from error

    async def async_get_devices(
        self, lan_tracking=False
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Get all devices."""
        devices_tracker = {}
        device_counters = {"wireless": 0, "wired": 0}
        parameters = {
            "expression": {
                "wifi": 'wifi && (edev || hnid) and .PhysAddress!=""',
                "eth": 'eth && (edev || hnid) and .PhysAddress!=""',
            }
        }
        devices = await self.api.devices.async_get_devices(parameters)
        devices_status_wireless = devices.get("status", {}).get("wifi", {})
        device_counters["wireless"] = len(devices_status_wireless)
        for device in devices_status_wireless:
            if device.get("Key"):
                devices_tracker.setdefault(device.get("Key"), {}).update(device)

        if lan_tracking:
            devices_status_wired = devices.get("status", {}).get("eth", {})
            device_counters["wired"] = len(devices_status_wired)
            for device in devices_status_wired:
                if device.get("Key"):
                    devices_tracker.setdefault(device.get("Key"), {}).update(device)

        return devices_tracker, device_counters

    async def async_get_caller_missed(self) -> dict[str, Any]:
        """Get caller missed."""
        cmisseds = []
        calls = await self.api.call.async_get_voiceapplication_calllist()
        for call in calls.get("status", {}):
            if call["callType"] != "succeeded":
                utc_dt = datetime.strptime(call["startTime"], "%Y-%m-%dT%H:%M:%SZ")
                local_dt = utc_dt.replace(tzinfo=UTC).astimezone(tz=DEFAULT_TIME_ZONE)
                cmisseds.append(
                    {
                        "phone_number": call["remoteNumber"],
                        "date": str(local_dt),
                        "callId": call["callId"],
                    }
                )

        return {"call missed": cmisseds}

    async def async_get_dsl_status(self) -> dict[str, Any]:
        """Get dsl status."""
        parameters = {"mibs": "dsl", "flag": "", "traverse": "down"}
        dsl_status = await self.api.connection.async_get_data_MIBS(parameters)
        return dsl_status.get("status", {}).get("dsl", {}).get("dsl0", {})

    async def async_get_infos(self) -> dict[str, Any]:
        """Get router infos."""
        infos = await self.api.deviceinfo.async_get_deviceinfo()
        return infos.get("status", {})

    async def async_get_wan_status(self):
        """Get status."""
        return await self.api.system.async_get_wanstatus()

    async def async_get_nmc(self) -> dict[str, Any]:
        """Get dsl status."""
        nmc = await self.api.system.async_get_nmc()
        return nmc.get("status", {})

    async def async_get_wifi(self) -> bool:
        """Get dsl status."""
        wifi = await self.api.wifi.async_get_wifi()
        return wifi.get("status", {}).get("Enable") is True

    async def async_get_guest_wifi(self) -> bool:
        """Get Guest Wifi status."""
        guest_wifi = await self.api.guestwifi.async_get_guest_wifi()
        return guest_wifi.get("status", {}).get("Enable") is True

    async def async_get_device_schedule(self, device_key):
        """Get device schedule."""
        parameters = {"type": "ToD", "ID": device_key}
        data = await self.api.schedule.async_get_schedule(parameters)
        return data.get("data", {}).get("scheduleInfo", {})
