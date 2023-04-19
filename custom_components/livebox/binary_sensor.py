"""Livebox binary sensor entities."""
import logging
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.const import ENTITY_CATEGORY_DIAGNOSTIC
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import COORDINATOR, DOMAIN, LIVEBOX_ID, MISSED_ICON
from .coordinator import LiveboxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Defer binary sensor setup to the shared sensor module."""
    datas = hass.data[DOMAIN][config_entry.entry_id]
    box_id = datas[LIVEBOX_ID]
    coordinator = datas[COORDINATOR]
    async_add_entities(
        [WanStatus(coordinator, box_id), CallMissed(coordinator, box_id)], True
    )


class WanStatus(CoordinatorEntity[LiveboxDataUpdateCoordinator], BinarySensorEntity):
    """Wan status sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_name = "WAN Status"

    def __init__(self, coordinator, box_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{box_id}_connectivity"
        self._attr_device_info = {"identifiers": {(DOMAIN, box_id)}}

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        wstatus = self.coordinator.data.get("wan_status", {}).get("data", {})
        return wstatus.get("WanState") == "up"

    @property
    def extra_state_attributes(self):
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

    def __init__(self, coordinator, box_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{box_id}_callmissed"
        self._attr_device_info = {"identifiers": {(DOMAIN, box_id)}}

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return len(self.coordinator.data.get("cmissed").get("call missed")) > 0

    @property
    def extra_state_attributes(self):
        """Return attributs."""
        return self.coordinator.data.get("cmissed")
