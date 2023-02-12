"""Sensor for Livebox router."""
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN, LIVEBOX_ID, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensors."""
    datas = hass.data[DOMAIN][config_entry.entry_id]
    box_id = datas[LIVEBOX_ID]
    coordinator = datas[COORDINATOR]
    nmc = coordinator.data["nmc"]
    entities = [
        FlowSensor(
            coordinator,
            box_id,
            description,
        )
        for description in SENSOR_TYPES
    ]
    if nmc.get("WanMode") is not None and "ETHERNET" not in nmc["WanMode"].upper():
        async_add_entities(entities, True)


class FlowSensor(CoordinatorEntity, SensorEntity):
    """Representation of a livebox sensor."""

    def __init__(self, coordinator, box_id, description):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attributs = description.attr
        self._current = description.current_rate
        self.entity_description = description
        self._attr_unique_id = f"{box_id}_{self._current}"
        self._attr_device_info = {"identifiers": {(DOMAIN, box_id)}}

    @property
    def native_value(self):
        """Return the native value of the device."""
        if self.coordinator.data["dsl_status"].get(self._current):
            return round(
                self.coordinator.data["dsl_status"][self._current] / 1000,
                2,
            )
        return None

    @property
    def extra_state_attributes(self):
        """Return the device state attributes."""
        attributs = {}
        for key, value in self._attributs.items():
            attributs[key] = self.coordinator.data["dsl_status"].get(value)
        return attributs
