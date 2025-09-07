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
from homeassistant.helpers.dispatcher import async_dispatcher_send
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
from .helpers import find_item

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
        self.model: int | float | None = None

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
                    self.model = 7.1
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
            callers, cmissed = await self.async_get_callers()

            await self.async_detect_new_dvices(devices)

            return {
                "cmissed": cmissed,
                "callers": callers,
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
                "lan": await self.async_get_lan(devices),
                "upnp": await self.async_get_port_forwarding(),
                "dhcp_leases": await self.async_get_dhcp_leases(),
                "guest_dhcp_leases": await self.async_get_dhcp_leases("guest"),
                "stats": await self.async_get_results(),
            }
        except AiosysbusException as error:
            _LOGGER.error("Error while fetch data information: %s", error)
            raise UpdateFailed(error) from error

    async def async_get_infos(self) -> dict[str, Any]:
        """Get router infos."""
        infos = (await self.api.deviceinfo.async_get_deviceinfo()).get("status", {})
        return infos

    async def async_get_devices(
        self, lan_tracking=False, wifi_tracking=True
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Get all devices."""
        devices_tracker = {}
        device_counters = {"wireless": 0, "wired": 0}
        mode = self.config_entry.options.get(
            CONF_DISPLAY_DEVICES, DEFAULT_DISPLAY_DEVICES
        )
        if mode == "All":
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
        devices = (
            await self._make_request(self.api.devices.async_get_devices, parameters)
        ).get("status", {})
        _LOGGER.debug("Fetch Devices: %s", devices)
        if wifi_tracking:
            device_counters["wireless"] = len(devices.get("wifi", {}))
            for device in devices.get("wifi", {}):
                if device.get("Key"):
                    devices_tracker.setdefault(device.get("Key"), {}).update(device)

        if lan_tracking:
            device_counters["wireless"] = len(devices.get("eth", {}))
            for device in devices.get("eth", {}):
                if device.get("Key"):
                    devices_tracker.setdefault(device.get("Key"), {}).update(device)

        return devices_tracker, device_counters

    async def async_get_caller_missed(self) -> list[dict[str, Any] | None]:
        """Get caller missed."""
        cmisseds = []
        calls = (
            await self._make_request(self.api.voiceservice.async_get_calllist)
        ).get("status", {})
        for call in calls:
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

    async def async_get_callers(self) -> tuple(list[dict[str, Any] | None]):
        """Get caller missed."""
        callers = []
        cmisseds = []
        calls = (
            await self._make_request(self.api.voiceservice.async_get_calllist)
        ).get("status", {})
        for call in calls:
            utc_dt = datetime.strptime(call["startTime"], "%Y-%m-%dT%H:%M:%SZ")
            local_dt = utc_dt.replace(tzinfo=UTC).astimezone(tz=DEFAULT_TIME_ZONE)
            caller = {
                "phone_number": call.get("remoteNumber"),
                "date": str(local_dt),
                "status": call.get("callType"),
                "duration": call.get("duration"),
                "id": call.get("callId"),
            }
            callers.append(caller)
            if call["callType"] == "missed":
                cmisseds.append(caller)

        return callers, cmisseds

    async def async_get_dsl_status(self) -> dict[str, Any]:
        """Get dsl status."""
        parameters = {"mibs": "dsl", "flag": "", "traverse": "down"}
        dsl0 = (
            await self._make_request(self.api.nemo.async_get_MIBs, "data", parameters)
        ).get("status", {})
        return find_item(dsl0, "dsl.dsl0", {})

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
        veip0 = (
            await self._make_request(self.api.nemo.async_get_MIBs, "veip0", parameters)
        ).get("status", {})
        return find_item(veip0, "gpon.veip0", {})

    async def async_get_lan(self, lan_devices):
        """Get lan status."""
        self_devices = (
            await self._make_request(
                self.api.devices.async_get_devices,
                {"expression": {"wifi": "vap && lan", "eth": "eth && lan"}},
            )
        ).get("status", {})

        wlanvap_data = (
            await self._make_request(
                self.api.nemo.async_get_MIBs, "lan", {"mibs": "wlanvap"}
            )
        ).get("status", {})

        devices = []
        for type, items in self_devices.items():
            for item in items:
                if type == "wifi":
                    intf = item.get("Name", "Unknown")
                    band = item.get("OperatingFrequencyBand", intf)
                    ess_identifier = item.get("EssIdentifier", "guest").lower()
                    wlanvap = wlanvap_data.get(intf, {})
                    devices.append(
                        {
                            "name": f"{band} ({ess_identifier})",
                            "status": item.get("Active"),
                            "type": "Wireless",
                            "extra_attributes": {
                                "last_change": item.get("LastChanged"),
                                "channel": item.get("Channel"),
                                "ssid": item.get("SSID"),
                                "associated_devices": wlanvap.get("AssociatedDevice"),
                            },
                        }
                    )
                if type == "eth":
                    devices.append(
                        {
                            "name": item.get("Name", "Unknown"),
                            "status": item.get("Active"),
                            "type": "Ethernet",
                            "extra_attributes": {
                                "current_bitrate": item.get("CurrentBitRate"),
                                "last_change": item.get("LastChanged"),
                                "port_state": item.get("PortState"),
                            },
                        }
                    )
        return devices

    async def async_get_wifi_stats(self) -> bool:
        """Get wifi stats."""
        stats = (await self._make_request(self.api.nmc.async_get_wifi_stats)).get(
            "data", {}
        )
        return stats

    async def async_get_fiber_stats(self) -> bool:
        """Get fiber stats."""
        if self.model == 4:
            intf = "eth0"
        elif self.model == 3:
            intf = "bridge_vmulti"
        else:
            intf = "veip0"
        stats = (
            await self._make_request(self.api.nemo.async_get_net_dev_stats, intf)
        ).get("status", {})
        return stats

    async def async_get_wan_status(self) -> dict[str, Any]:
        """Get status."""
        wan_status = (await self._make_request(self.api.nmc.async_get_wan_status)).get(
            "data", {}
        )
        return wan_status

    async def async_get_nmc(self) -> dict[str, Any]:
        """Get dsl status."""
        nmc = (await self._make_request(self.api.nmc.async_get)).get("status", {})
        return nmc

    async def async_is_wifi(self) -> bool:
        """Get wireless status."""
        wifi = (await self._make_request(self.api.nmc.async_get_wifi)).get("status", {})
        return wifi.get("Enable") is True

    async def async_is_guest_wifi(self) -> bool:
        """Get Guest Wifi status."""
        guest_wifi = (await self._make_request(self.api.nmc.async_get_guest_wifi)).get(
            "status", {}
        )
        return guest_wifi.get("Enable") is True

    async def async_get_ddns(self) -> list[Any]:
        """Get DDNS status."""
        ddns = (await self._make_request(self.api.dyndns.async_get_hosts)).get(
            "status", {}
        )
        return ddns if isinstance(ddns, list) else []

    async def async_get_device_schedule(self, device_key):
        """Get device schedule."""
        parameters = {"type": "ToD", "ID": device_key}
        data = (
            await self._make_request(self.api.schedule.async_get_schedule, parameters)
        ).get("data", {})
        return data.get("scheduleInfo", {})

    async def async_is_remote_access(self) -> bool:
        """Get Remote access status."""
        ra = (await self._make_request(self.api.remoteaccess.async_get)).get(
            "status", {}
        )
        return ra.get("Enable", False) is True

    async def async_detect_new_dvices(self, devices) -> None:
        """New devices detected."""
        if self.data and self.data.get("devices"):
            for key in devices:
                if key not in self.data.get("devices", {}):
                    self.data["devices"] = devices
                    async_dispatcher_send(self.hass, self.signal_device_new)
                    async_dispatcher_send(self.hass, self.signal_wan_access_new)
                    break

    async def async_get_port_forwarding(self) -> list[dict[str, Any]]:
        """Get port forwarding."""
        port_forwarding = (
            await self._make_request(self.api.firewall.async_get_port_forwarding)
        ).get("status", {})
        ports = []
        for port in port_forwarding.values():
            if not port.get("Enable"):
                continue
            ports.append(
                {
                    "id": port.get("Id"),
                    "Ext. Ip": port.get("DestinationIPAddress"),
                    "Ext. Port": port.get("ExternalPort"),
                    "internal port": port.get("InternalPort"),
                }
            )

        return ports

    async def async_get_dhcp_leases(
        self, domain: str = "default"
    ) -> list[dict[str, Any]]:
        """Get dhcp leases."""
        data = (
            await self._make_request(self.api.dhcp.async_get_dhcp_leases, None, domain)
        ).get("status", {})
        leases = []
        for item in data.get(domain, {}).values():
            leases.append(
                {
                    "id": item.get("IPAddress"),
                    "mac_address": item.get("MACAddress"),
                    "name": item.get("FriendlyName"),
                    "time": item.get("LeaseTime"),
                    "enable": item.get("Active"),
                    "reserved": item.get("Reserved"),
                }
            )
        return leases

    async def async_get_results(self) -> dict[str, Any]:
        """Get interfaces."""
        results = {}

        data = (await self._make_request(self.api.homelan.async_get_interface)).get(
            "status", {}
        )

        interfaces = {
            item["FriendlyName"]: item
            for item in data.values()
            if "Name" in item and "FriendlyName" in item and "vlan" not in item["Name"]
        }

        data = (
            await self._make_request(
                self.api.homelan.async_get_results,
                {"InterfaceName": list(interfaces.keys()), "NumberOfReadings": 1},
            )
        ).get("status", {})

        for key, item in interfaces.items():
            traffic = data.get(key, {}).get("Traffic", [])
            if len(traffic) == 0:
                continue
            stats = traffic[0]

            # Rx_Counter and Tx_Counter => bits/30seconds
            #  /8 => octets , / 30 => 1seconds (8*30 => 240)
            # /1048576 => MBytes

            results.update(
                {
                    item["Name"]: {
                        "friendly_name": key,
                        "alias": item.get("alias"),
                        "rate_rx": round(stats.get("Rx_Counter", 0) / 240 / 1048576, 2),
                        "rate_tx": round(stats.get("Tx_Counter", 0) / 240 / 1048576, 2),
                    }
                }
            )
        return results

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

    @property
    def signal_wan_access_new(self) -> str:
        """Event specific per Livebox entry to signal new device."""
        return f"{DOMAIN}-{self.unique_id}-wan-accessnew"
