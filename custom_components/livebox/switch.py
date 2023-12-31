"""Sensor for Livebox router."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DEVICE_WANACCESS_ICON, DOMAIN, GUESTWIFI_ICON, LIVEBOX_API, LIVEBOX_ID
from .coordinator import LiveboxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensors."""
    datas = hass.data[DOMAIN][config_entry.entry_id]
    box_id = datas[LIVEBOX_ID]
    api = datas[LIVEBOX_API]
    coordinator = datas[COORDINATOR]
    async_add_entities([WifiSwitch(coordinator, box_id, api)], True)
    async_add_entities([GuestWifiSwitch(coordinator, box_id, api)], True)
    async_add_entities(
        [
            DeviceWANAccessSwitch(coordinator, box_id, api, key, device)
            for key, device in coordinator.data["devices"].items()
        ],
        True,
    )


class WifiSwitch(CoordinatorEntity[LiveboxDataUpdateCoordinator], SwitchEntity):
    """Representation of a livebox sensor."""

    _attr_name = "Wifi switch"
    _attr_has_entity_name = True

    def __init__(self, coordinator, box_id, api):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._api = api
        self._attr_unique_id = f"{box_id}_wifi"
        self._attr_device_info = {"identifiers": {(DOMAIN, box_id)}}

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.coordinator.data.get("wifi")

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        parameters = {"Enable": "true", "Status": "true"}
        await self.hass.async_add_executor_job(self._api.wifi.set_wifi, parameters)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        parameters = {"Enable": "false", "Status": "false"}
        await self.hass.async_add_executor_job(self._api.wifi.set_wifi, parameters)
        await self.coordinator.async_request_refresh()


class GuestWifiSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a livebox sensor."""

    _attr_name = "Guest Wifi switch"
    _attr_icon = GUESTWIFI_ICON
    _attr_has_entity_name = True

    def __init__(self, coordinator, box_id, api):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._api = api
        self._attr_unique_id = f"{box_id}_guest_wifi"
        self._attr_device_info = {"identifiers": {(DOMAIN, box_id)}}

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.coordinator.data.get("guest_wifi")

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        parameters = {"Enable": "true", "Status": "true"}
        await self.hass.async_add_executor_job(
            self._api.guestwifi.set_guest_wifi, parameters
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        parameters = {"Enable": "false", "Status": "false"}
        await self.hass.async_add_executor_job(
            self._api.guestwifi.set_guest_wifi, parameters
        )
        await self.coordinator.async_request_refresh()


class DeviceWANAccessSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a livebox device WAN access switch."""

    _attr_name = "WAN access"
    _attr_icon = DEVICE_WANACCESS_ICON
    _attr_has_entity_name = True

    def __init__(self, coordinator, box_id, api, device_key, device):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._box_id = box_id
        self._api = api
        self._device_key = device_key
        self._device = device

        self._attr_name = "WAN access"
        self._attr_unique_id = f"{self._device_key}_wan_access"
        self._attr_device_info = {
            "name": self._device.get("Name"),
            "identifiers": {(DOMAIN, self._device_key)},
            "via_device": (DOMAIN, self._box_id),
        }

    def _get_device_schedule(self):
        """Get device schedule"""
        return self.coordinator.data.get("devices_wan_access", {}).get(
            self._device_key, False
        )

    @property
    def is_on(self):
        """Return true if device currently have WAN access."""
        schedule = self._get_device_schedule()
        _LOGGER.debug(
            "Device %s (%s) schedule: %s",
            self._device.get("Name"),
            self._device_key,
            schedule,
        )
        if (
            schedule
            and (schedule.get("override") == "Disable")
            and (schedule.get("value") == "Disable")
        ):
            _LOGGER.debug(
                "Locking schedule found for device %s (%s), WAN access OFF",
                self._device.get("Name"),
                self._device_key,
            )
            return False
        _LOGGER.debug(
            "No locking schedule found for device %s (%s), WAN access is ON",
            self._device.get("Name"),
            self._device_key,
        )
        return True

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        schedule = self._get_device_schedule()
        _LOGGER.debug(
            "Unlock WAN access of device %s (%s)",
            self._device.get("Name"),
            self._device_key,
        )
        if schedule:
            _LOGGER.debug(
                "Schedule found for device %s (%s): %s",
                self._device.get("Name"),
                self._device_key,
                schedule,
            )
            parameters = {"type": "ToD", "ID": self._device_key, "override": "Enable"}
            _LOGGER.debug(
                "Set device %s (%s) schedule: %s",
                self._device.get("Name"),
                self._device_key,
                parameters,
            )
            result = await self.hass.async_add_executor_job(
                self._api.schedule.set_schedule, parameters
            )
            if not isinstance(result, dict) or not result.get("status"):
                raise HomeAssistantError(
                    f"Fail to unlock device {self._device.get('Name')} ({self._device_key}) "
                    "WAN access"
                )
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.debug(
                "No schedule found for device %s (%s), WAN access is already unlocked",
                self._device.get("Name"),
                self._device_key,
            )

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        schedule = self._get_device_schedule()
        _LOGGER.info(
            "Lock WAN access of device %s (%s)",
            self._device.get("Name"),
            self._device_key,
        )
        if schedule:
            _LOGGER.debug(
                "Schedule found for device %s (%s), update it to lock WAN access",
                self._device.get("Name"),
                self._device_key,
            )
            parameters = {"type": "ToD", "ID": self._device_key, "override": "Disable"}
            result = await self.hass.async_add_executor_job(
                self._api.schedule.set_schedule, parameters
            )
            if not isinstance(result, dict) or not result.get("status"):
                raise HomeAssistantError(
                    f"Fail to lock device {self._device.get('Name')} ({self._device_key}) "
                    "WAN access"
                )
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.debug(
                "No schedule found for device %s (%s), add one to lock WAN access",
                self._device.get("Name"),
                self._device_key,
            )
            parameters = {
                "type": "ToD",
                "ID": self._device_key,
                "info": {
                    "base": "Weekly",
                    "def": "Enable",
                    "ID": self._device_key,
                    "schedule": [],
                    "enable": True,
                    "override": "Disable",
                },
            }
            result = await self.hass.async_add_executor_job(
                self._api.schedule.add_schedule, parameters
            )
            if not isinstance(result, dict) or not result.get("status"):
                raise HomeAssistantError(
                    f"Fail to lock device {self._device.get('Name')} ({self._device_key}) "
                    "WAN access"
                )
            await self.coordinator.async_request_refresh()
