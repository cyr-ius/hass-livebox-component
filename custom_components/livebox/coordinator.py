"""Coordinator for Livebox."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from aiosysbus import AIOSysbus
from aiosysbus.exceptions import AiosysbusException
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import DEFAULT_TIME_ZONE, UTC

from .const import (
    CONF_DISPLAY_DEVICES,
    CONF_LAN_TRACKING,
    CONF_USE_TLS,
    CONF_WIFI_TRACKING,
    DEFAULT_DISPLAY_DEVICES,
    DEFAULT_LAN_TRACKING,
    DEFAULT_WIFI_TRACKING,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=1)


class LiveboxDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to fetch data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Class to manage fetching data API."""
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.config_entry = config_entry
        self.api = AIOSysbus(
            username=config_entry.data[CONF_USERNAME],
            password=config_entry.data[CONF_PASSWORD],
            session=async_create_clientsession(hass),
            host=config_entry.data[CONF_HOST],
            port=config_entry.data[CONF_PORT],
            use_tls=config_entry.data.get(CONF_USE_TLS, False),
        )
        self.unique_id: str | None = None
        self.model: int | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data."""
        try:
            # Mandatory information
            infos = await self.async_get_infos()
            self.unique_id = infos["SerialNumber"]
            match infos["ProductClass"]:
                case "Livebox 3":
                    self.model = 3
                case "Livebox 4":
                    self.model = 4
                case "Livebox Fibre":
                    self.model = 5
                case "Livebox 6":
                    self.model = 6
                case "Livebox 7":
                    self.model = 7
                case "Livebox W7":
                    self.model = 7
                case "SMBSLBFIBRA":
                    self.model = 5656  # Sagemcom f@st 5656
            # Optionals
            wifi_tracking = self.config_entry.options.get(
                CONF_WIFI_TRACKING, DEFAULT_WIFI_TRACKING
            )
            lan_tracking = self.config_entry.options.get(
                CONF_LAN_TRACKING, DEFAULT_LAN_TRACKING
            )
            devices, device_counters = await self.async_get_devices(
                lan_tracking, wifi_tracking
            )
            return {
                "cmissed": await self.async_get_caller_missed(),
                "devices": devices,
                "dsl_status": await self.async_get_dsl_status(),
                "infos": infos,
                "nmc": await self.async_get_nmc(),
                "wan_status": await self.async_get_wan_status(),
                "wifi": await self.async_is_wifi(),
                "guest_wifi": await self.async_is_guest_wifi(),
                "count_wired_devices": device_counters["wired"],
                "count_wireless_devices": device_counters["wireless"],
                "devices_wan_access": {
                    key: await self.async_get_device_schedule(key) for key in devices
                },
                "ddns": await self.async_get_ddns(),
                "wifi_stats": await self.async_get_wifi_stats(),
                "fiber_status": await self.async_get_fiber_status(),
                "fiber_stats": await self.async_get_fiber_stats(),
                "remote_access": await self.async_is_remote_access(),
            }
        except AiosysbusException as error:
            _LOGGER.error("Error while fetch data information: %s", error)
            raise UpdateFailed(error) from error

    async def async_get_infos(self) -> dict[str, Any]:
        """Get router infos."""
        infos = await self.api.deviceinfo.async_get_deviceinfo()
        return infos.get("status", {})

    async def async_get_devices(
        self, lan_tracking=False, wifi_tracking=True
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Get all devices."""
        devices_tracker = {}
        device_counters = {"wireless": 0, "wired": 0}
        device_tracker_mode = self.config_entry.options.get(
            CONF_DISPLAY_DEVICES, DEFAULT_DISPLAY_DEVICES
        )
        if device_tracker_mode == "All":
            parameters = {
                "expression": {
                    "wifi": 'wifi && (edev || hnid) and .PhysAddress!=""',
                    "eth": 'eth && (edev || hnid) and .PhysAddress!=""',
                }
            }
        else:
            parameters = {
                "expression": {
                    "wifi": '.Active==true && wifi && (edev || hnid) and .PhysAddress!=""',
                    "eth": '.Active==true && eth && (edev || hnid) and .PhysAddress!=""',
                }
            }
        devices = await self._make_request(
            self.api.devices.async_get_devices, parameters
        )
        _LOGGER.debug("Fetch Devices: %s", devices)
        if wifi_tracking:
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

    async def async_get_caller_missed(self) -> list[dict[str, Any] | None]:
        """Get caller missed."""
        cmisseds = []
        calls = await self._make_request(self.api.voiceservice.async_get_calllist)
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

        return cmisseds

    async def async_get_dsl_status(self) -> dict[str, Any]:
        """Get dsl status."""
        parameters = {"mibs": "dsl", "flag": "", "traverse": "down"}
        dsl0 = await self._make_request(
            self.api.nemo.async_get_MIBs, "data", parameters
        )
        return dsl0.get("status", {}).get("dsl", {}).get("dsl0", {})

    async def async_get_fiber_status(self):
        """Get fiber status."""
        if self.model in [4, 3]:
            return {}
        if self.model == 5656:
            optical = (
                await self._make_request(self.api.sgcomci.async_get_optical)
            ).get("status", {})
            return {
                "SignalTxPower": float(optical.get("PowerTx", 0)) * 1000,
                "SignalRxPower": float(optical.get("PowerRx", 0)) * 1000,
                "Temperature": float(optical.get("Temperature", 0)),
                "Voltage": float(optical.get("Vcc", 0)),
                "Bias": float(optical.get("BiasCurrent", 0)),
            }

        parameters = {"mibs": "gpon"}
        veip0 = await self._make_request(
            self.api.nemo.async_get_MIBs, "veip0", parameters
        )
        return veip0.get("status", {}).get("gpon", {}).get("veip0", {})

    async def async_get_wifi_stats(self) -> bool:
        """Get wifi stats."""
        stats = await self._make_request(self.api.nmc.async_get_wifi_stats)
        return stats.get("data", {})

    async def async_get_fiber_stats(self) -> bool:
        """Get fiber stats."""
        if self.model == 4:
            intf = "eth0"
        elif self.model == 3:
            intf = "bridge_vmulti"
        else:
            intf = "veip0"
        stats = await self._make_request(self.api.nemo.async_get_net_dev_stats, intf)
        return stats.get("status", {})

    async def async_get_wan_status(self) -> dict[str, Any]:
        """Get status."""
        wan_status = await self._make_request(self.api.nmc.async_get_wan_status)
        return wan_status.get("data", {})

    async def async_get_nmc(self) -> dict[str, Any]:
        """Get dsl status."""
        nmc = await self._make_request(self.api.nmc.async_get)
        return nmc.get("status", {})

    async def async_is_wifi(self) -> bool:
        """Get dsl status."""
        wifi = await self._make_request(self.api.nmc.async_get_wifi)
        return wifi.get("status", {}).get("Enable") is True

    async def async_is_guest_wifi(self) -> bool:
        """Get Guest Wifi status."""
        guest_wifi = await self._make_request(self.api.nmc.async_get_guest_wifi)
        return guest_wifi.get("status", {}).get("Enable") is True

    async def async_get_ddns(self) -> bool:
        """Get DDNS status."""
        ddns = await self._make_request(self.api.dyndns.async_get_hosts)
        return ddns.get("status") if isinstance(ddns.get("status"), list) else []

    async def async_get_device_schedule(self, device_key):
        """Get device schedule."""
        parameters = {"type": "ToD", "ID": device_key}
        data = await self._make_request(
            self.api.schedule.async_get_schedule, parameters
        )
        return data.get("data", {}).get("scheduleInfo", {})

    async def async_is_remote_access(self) -> bool:
        """Get Remote access status."""
        ra = await self._make_request(self.api.remoteaccess.async_get)
        return ra.get("status", {}).get("Enable", False) is True

    async def _make_request(
        self, func: Callable[..., Any], *args: Any
    ) -> dict[str, Any]:
        """Execute request."""
        try:
            return await func(*args)
        except AiosysbusException as error:
            _LOGGER.error("Error while execute: %s (%s)", func.__name__, error)
        return {}

    @property
    def signal_device_new(self) -> str:
        """Event specific per Livebox entry to signal new device."""
        return f"{DOMAIN}-{self.unique_id}-device-new"
