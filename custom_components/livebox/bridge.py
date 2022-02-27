"""Collect datas information from livebox."""
import logging
from datetime import datetime

from aiosysbus import AIOSysbus
from aiosysbus.exceptions import (
    AuthorizationError,
    HttpRequestError,
    InsufficientPermissionsError,
    LiveboxException,
    NotOpenError,
)
from homeassistant.util.dt import (
    UTC,
    DEFAULT_TIME_ZONE,
)
from .const import CALLID, CONF_LAN_TRACKING

_LOGGER = logging.getLogger(__name__)


class BridgeData:
    """Simplification of API calls."""

    def __init__(self, hass, config_entry=None, config_flow_data=None):
        """Init parameters."""
        self._hass = hass
        self.config_entry = config_entry
        if config_entry is not None:
            self.data_config = config_entry.data
        if config_flow_data is not None:
            self.data_config = config_flow_data
        self.api = None
        self.count_wired_devices = 0
        self.count_wireless_devices = 0

    async def async_connect(self):
        """Connect at livebox."""
        self.api = AIOSysbus(
            username=self.data_config["username"],
            password=self.data_config["password"],
            host=self.data_config["host"],
            port=self.data_config["port"],
        )

        try:
            await self._hass.async_add_executor_job(self.api.connect)
        except AuthorizationError as error:
            _LOGGER.error("Error Authorization (%s)", error)
            raise AuthorizationError from error
        except NotOpenError as error:
            _LOGGER.error("Error Not open (%s)", error)
            raise NotOpenError from error
        except LiveboxException as error:
            _LOGGER.error("Error Unknown (%s)", error)
            raise LiveboxException from error

        try:
            await self._hass.async_add_executor_job(self.api.get_permissions)
        except InsufficientPermissionsError as error:
            _LOGGER.error("Error Insufficient Permissions (%s)", error)
            raise InsufficientPermissionsError from error

    async def async_make_request(self, call_api, **kwargs):
        """Make request for API."""
        try:
            return await self._hass.async_add_executor_job(call_api, kwargs)
        except HttpRequestError as error:
            _LOGGER.error("HTTP Request (%s)", error)
        except LiveboxException as error:
            _LOGGER.error("Error Unknown (%s)", error)
        return {}

    async def async_fetch_datas(self):
        """Fetch datas."""
        return {
            "cmissed": await self.async_get_caller_missed(),
            "devices": await self.async_get_devices(),
            "dsl_status": await self.async_get_dsl_status(),
            "infos": await self.async_get_infos(),
            "nmc": await self.async_get_nmc(),
            "wan_status": await self.async_get_wan_status(),
            "wifi": await self.async_get_wifi(),
            "count_wired_devices": self.count_wired_devices,
            "count_wireless_devices": self.count_wireless_devices,
        }

    async def async_get_devices(self):
        """Get all devices."""
        devices_tracker = {}
        parameters = {
            "expression": {
                "wifi": 'wifi && (edev || hnid) and .PhysAddress!=""',
                "eth": 'eth && (edev || hnid) and .PhysAddress!=""',
            }
        }
        devices = await self.async_make_request(
            self.api.devices.get_devices, **parameters
        )
        devices_status_wireless = devices.get("status", {}).get("wifi", {})
        self.count_wireless_devices = len(devices_status_wireless)
        for device in devices_status_wireless:
            if device.get("Key"):
                devices_tracker.setdefault(device.get("Key"), {}).update(device)

        if self.config_entry.options.get(CONF_LAN_TRACKING, False):
            devices_status_wired = devices.get("status", {}).get("eth", {})
            self.count_wired_devices = len(devices_status_wired)
            for device in devices_status_wired:
                if device.get("Key"):
                    devices_tracker.setdefault(device.get("Key"), {}).update(device)

        return devices_tracker

    async def async_get_infos(self):
        """Get router infos."""
        infos = await self.async_make_request(self.api.deviceinfo.get_deviceinfo)
        return infos.get("status", {})

    async def async_get_wan_status(self):
        """Get status."""
        wan_status = await self.async_make_request(self.api.system.get_wanstatus)
        return wan_status

    async def async_get_caller_missed(self):
        """Get caller missed."""
        cmisseds = []
        calls = await self.async_make_request(
            self.api.call.get_voiceapplication_calllist
        )

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

    async def async_get_dsl_status(self):
        """Get dsl status."""
        parameters = {"mibs": "dsl", "flag": "", "traverse": "down"}
        dsl_status = await self.async_make_request(
            self.api.connection.get_data_MIBS, **parameters
        )
        return dsl_status.get("status", {}).get("dsl", {}).get("dsl0", {})

    async def async_get_nmc(self):
        """Get dsl status."""
        nmc = await self.async_make_request(self.api.system.get_nmc)
        return nmc.get("status", {})

    async def async_get_wifi(self):
        """Get dsl status."""
        wifi = await self.async_make_request(self.api.wifi.get_wifi)
        return wifi.get("status", {}).get("Enable") is True

    async def async_remove_cmissed(self, call) -> None:
        """Remove call missed."""
        await self.async_make_request(
            self.api.call.get_voiceapplication_clearlist,
            **{CALLID: call.data.get(CALLID)},
        )
