"""Livebox binary sensor entities."""
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MISSED_ICON
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Defer binary sensor setup to the shared sensor module."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WanStatus(coordinator), CallMissed(coordinator)], True)


class WanStatus(LiveboxEntity, BinarySensorEntity):
    """Wan status sensor."""

    def __init__(self, coordinator: LiveboxDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        description = BinarySensorEntityDescription(
            key="connectivity",
            name="WAN Status",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            entity_category=EntityCategory.DIAGNOSTIC,
        )
        super().__init__(coordinator, description)

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        wan_status = self.coordinator.data.get("wan_status", {})
        return wan_status.get("WanState") == "up"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        wan_status = self.coordinator.data.get("wan_status", {})
        uptime = datetime.today() - timedelta(
            seconds=self.coordinator.data["infos"].get("UpTime", 0)
        )
        return {
            "link_type": wan_status.get("LinkType"),
            "link_state": wan_status.get("LinkState"),
            "last_connection_error": wan_status.get("LastConnectionError"),
            "wan_ipaddress": wan_status.get("IPAddress"),
            "wan_ipv6address": wan_status.get("IPv6Address"),
            "wan_ipv6prefix": wan_status.get("IPv6DelegatedPrefix"),
            "uptime": uptime,
            "wired clients": self.coordinator.data.get("count_wired_devices"),
            "wireless clients": self.coordinator.data.get("count_wireless_devices"),
        }


class CallMissed(LiveboxEntity, BinarySensorEntity):
    """Call missed sensor."""

    def __init__(self, coordinator: LiveboxDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        description = BinarySensorEntityDescription(
            key="callmissed", icon=MISSED_ICON, name="Call missed"
        )
        super().__init__(coordinator, description)

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return len(self.coordinator.data.get("cmissed", {}).get("call missed", [])) > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes."""
        return self.coordinator.data.get("cmissed")
