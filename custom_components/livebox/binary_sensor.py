"""Livebox binary sensor entities."""
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MISSED_ICON
from .coordinator import LiveboxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Defer binary sensor setup to the shared sensor module."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WanStatus(coordinator), CallMissed(coordinator)], True)


class WanStatus(CoordinatorEntity[LiveboxDataUpdateCoordinator], BinarySensorEntity):
    """Wan status sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_name = "WAN Status"

    def __init__(self, coordinator: LiveboxDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_connectivity"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.unique_id)}}

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        wstatus = self.coordinator.data.get("wan_status", {}).get("data", {})
        return wstatus.get("WanState") == "up"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        wstatus = self.coordinator.data.get("wan_status", {}).get("data", {})
        uptime = datetime.today() - timedelta(
            seconds=self.coordinator.data["infos"].get("UpTime")
        )
        _attributs = {
            "link_type": wstatus.get("LinkType"),
            "link_state": wstatus.get("LinkState"),
            "last_connection_error": wstatus.get("LastConnectionError"),
            "wan_ipaddress": wstatus.get("IPAddress"),
            "wan_ipv6address": wstatus.get("IPv6Address"),
            "wan_ipv6prefix": wstatus.get("IPv6DelegatedPrefix"),
            "uptime": uptime,
        }
        cwired = self.coordinator.data.get("count_wired_devices")
        if cwired > 0:
            _attributs.update({"wired clients": cwired})
        cwireless = self.coordinator.data.get("count_wireless_devices")
        if cwireless > 0:
            _attributs.update({"wireless clients": cwireless})

        return _attributs


class CallMissed(CoordinatorEntity[LiveboxDataUpdateCoordinator], BinarySensorEntity):
    """Call missed sensor."""

    _attr_name = "Call missed"
    _attr_icon = MISSED_ICON
    _attr_has_entity_name = True

    def __init__(self, coordinator: LiveboxDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_callmissed"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.unique_id)}}

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return len(self.coordinator.data.get("cmissed", {}).get("call missed", [])) > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes."""
        return self.coordinator.data.get("cmissed")
