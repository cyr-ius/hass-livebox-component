"""Sensor for Livebox router."""
import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_TYPES
from .coordinator import LiveboxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [FlowSensor(coordinator, description) for description in SENSOR_TYPES]

    nmc = coordinator.data.get("nmc", {})
    if nmc.get("WanMode") and "ETHERNET" not in nmc["WanMode"].upper():
        async_add_entities(entities, True)


class FlowSensor(CoordinatorEntity[LiveboxDataUpdateCoordinator], SensorEntity):
    """Representation of a livebox sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr = description.attr
        self._current = description.current_rate
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.unique_id}_{self._current}"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.unique_id)}}

    @property
    def native_value(self) -> float | None:
        """Return the native value of the device."""
        if self.coordinator.data["dsl_status"].get(self._current):
            return round(
                self.coordinator.data["dsl_status"][self._current] / 1000,
                2,
            )
        return None

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the device state attributes."""
        attr = {}
        for key, value in self._attr.items():
            attr[key] = self.coordinator.data["dsl_status"].get(value)
        return attr
