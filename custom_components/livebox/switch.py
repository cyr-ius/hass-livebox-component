"""Sensor for Livebox router."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_WANACCESS_ICON, DOMAIN, GUESTWIFI_ICON
from .coordinator import LiveboxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [GuestWifiSwitch(coordinator), WifiSwitch(coordinator)]
    for key, device in coordinator.data["devices"].items():
        entities.append(DeviceWANAccessSwitch(coordinator, key, device))

    async_add_entities(entities, True)


class WifiSwitch(CoordinatorEntity[LiveboxDataUpdateCoordinator], SwitchEntity):
    """Representation of a livebox sensor."""

    _attr_name = "Wifi switch"
    _attr_has_entity_name = True

    def __init__(self, coordinator: LiveboxDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_wifi"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.unique_id)}}

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self.coordinator.data.get("wifi") is True

    async def async_turn_on(self) -> None:
        """Turn the switch on."""
        parameters = {"Enable": "true", "Status": "true"}
        await self.coordinator.api.wifi.async_set_wifi(parameters)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn the switch off."""
        parameters = {"Enable": "false", "Status": "false"}
        await self.coordinator.api.wifi.async_set_wifi(parameters)
        await self.coordinator.async_request_refresh()


class GuestWifiSwitch(CoordinatorEntity[LiveboxDataUpdateCoordinator], SwitchEntity):
    """Representation of a livebox sensor."""

    _attr_name = "Guest Wifi switch"
    _attr_icon = GUESTWIFI_ICON
    _attr_has_entity_name = True

    def __init__(self, coordinator: LiveboxDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_guest_wifi"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.unique_id)}}

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self.coordinator.data.get("guest_wifi") is True

    async def async_turn_on(self) -> None:
        """Turn the switch on."""
        parameters = {"Enable": "true", "Status": "true"}
        await self.coordinator.api.guestwifi.async_set_guest_wifi, parameters()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn the switch off."""
        parameters = {"Enable": "false", "Status": "false"}
        await self.coordinator.api.guestwifi.async_set_guest_wifi(parameters)
        await self.coordinator.async_request_refresh()


class DeviceWANAccessSwitch(
    CoordinatorEntity[LiveboxDataUpdateCoordinator], SwitchEntity
):
    """Representation of a livebox device WAN access switch."""

    _attr_name = "WAN access"
    _attr_icon = DEVICE_WANACCESS_ICON
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        device_key: str,
        device: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_key = device_key
        self._device = device
        self._attr_name = "WAN access"
        self._attr_unique_id = f"{self._device_key}_wan_access"
        self._attr_device_info = {
            "name": self._device.get("Name"),
            "identifiers": {(DOMAIN, self._device_key)},
            "connections": {(dr.CONNECTION_NETWORK_MAC, self._device_key)},
            "via_device": (DOMAIN, coordinator.unique_id),
        }

    def _get_device_schedule(self) -> dict[str, Any]:
        """Get device schedule."""
        return self.coordinator.data.get("devices_wan_access", {}).get(
            self._device_key, False
        )

    @property
    def is_on(self) -> bool:
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

    async def async_turn_on(self) -> None:
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
            result = await self.coordinator.api.schedule.async_set_schedule(parameters)
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

    async def async_turn_off(self) -> None:
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
            result = await self.coordinator.api.schedule.async_set_schedule(parameters)
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
            result = await self.coordinator.api.schedule.async_add_schedule(parameters)
            if not isinstance(result, dict) or not result.get("status"):
                raise HomeAssistantError(
                    f"Fail to lock device {self._device.get('Name')} ({self._device_key}) "
                    "WAN access"
                )
            await self.coordinator.async_request_refresh()
