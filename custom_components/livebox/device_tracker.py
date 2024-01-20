"""Support for the Livebox platform."""
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TRACKING_TIMEOUT, DEFAULT_TRACKING_TIMEOUT, DOMAIN
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up device tracker from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        LiveboxDeviceScannerEntity(
            coordinator, SensorEntityDescription(key=f"{uid}_tracker"), device
        )
        for uid, device in coordinator.data.get("devices", {}).items()
        if "IPAddress" and "PhysAddress" in device
    ]
    async_add_entities(entities, True)


class LiveboxDeviceScannerEntity(LiveboxEntity, ScannerEntity):
    """Represent a tracked device."""

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        description: SensorEntityDescription,
        device: dict[str, Any],
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator, description)
        self._device = device
        self._old_status = datetime.today()
        self._attr_name = device.get("Name")
        self._attr_unique_id = device.get("Key")
        self._attr_device_info = {
            "name": device.get("Name"),
            "identifiers": {(DOMAIN, device.get("Key"))},
            "via_device": (DOMAIN, coordinator.unique_id),
        }

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected to the network."""
        timeout_tracking = self.coordinator.config_entry.options.get(
            CONF_TRACKING_TIMEOUT, DEFAULT_TRACKING_TIMEOUT
        )
        device = self.coordinator.data.get("devices", {}).get(self.unique_id, {})
        status = device.get("Active", False)
        if status is True:
            self._old_status = datetime.today() + timedelta(seconds=timeout_tracking)
        if status is False and self._old_status > datetime.today():
            _LOGGER.debug("%s will be disconnected at %s", self.name, self._old_status)
            return True

        return status

    @property
    def source_type(self) -> SourceType:
        """Return the source type, eg gps or router, of the device."""
        return SourceType.ROUTER

    @property
    def ip_address(self) -> str:
        """Return ip address."""
        return self._device.get("IPAddress")

    @property
    def mac_address(self) -> str:
        """Return mac address."""
        return self._device.get("Key")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        return {"first_seen": self._device.get("FirstSeen")}
