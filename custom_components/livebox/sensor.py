"""Sensor for Livebox router."""
import logging
from dataclasses import dataclass
from typing import Final

from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import DATA_RATE_MEGABITS_PER_SECOND

from .const import COORDINATOR, DOMAIN, LIVEBOX_ID

_LOGGER = logging.getLogger(__name__)


@dataclass
class FlowSensorEntityDescription(SensorEntityDescription):
    """Represents an Flow Sensor."""

    current_rate: str = None
    attr: dict = None


SENSOR_TYPES: Final[tuple[SensorEntityDescription, ...]] = (
    FlowSensorEntityDescription(
        key="down",
        name="Orange Livebox Download speed",
        current_rate="DownstreamCurrRate",
        native_unit_of_measurement=DATA_RATE_MEGABITS_PER_SECOND,
        state_class=STATE_CLASS_MEASUREMENT,
        attr={
            "downstream_maxrate": "DownstreamMaxRate",
            "downstream_lineattenuation": "DownstreamLineAttenuation",
            "downstream_noisemargin": "DownstreamNoiseMargin",
            "downstream_power": "DownstreamPower",
        },
    ),
    FlowSensorEntityDescription(
        key="up",
        name="Orange Livebox Upload speed",
        current_rate="UpstreamCurrRate",
        native_unit_of_measurement=DATA_RATE_MEGABITS_PER_SECOND,
        state_class=STATE_CLASS_MEASUREMENT,
        attr={
            "upstream_maxrate": "UpstreamMaxRate",
            "upstream_lineattenuation": "UpstreamLineAttenuation",
            "upstream_noisemargin": "UpstreamNoiseMargin",
            "upstream_power": "UpstreamPower",
        },
    ),
)


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


class FlowSensor(SensorEntity):
    """Representation of a livebox sensor."""

    should_poll = False

    def __init__(
        self,
        coordinator,
        box_id,
        description: SensorEntityDescription,
    ):
        """Initialize the sensor."""
        self.box_id = box_id
        self.coordinator = coordinator
        self._attributs = description.attr
        self._current = description.current_rate
        self.entity_description = description

    @property
    def unique_id(self):
        """Return unique_id."""
        cr = self._current
        return f"{self.box_id}_{cr}"

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
    def device_info(self):
        """Return the device info."""
        return {"identifiers": {(DOMAIN, self.box_id)}}

    @property
    def extra_state_attributes(self):
        """Return the device state attributes."""
        _attributs = {}
        for key, value in self._attributs.items():
            _attributs[key] = self.coordinator.data["dsl_status"].get(value)
        return _attributs

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.

        Only used by the generic entity update service.
        """
        await self.coordinator.async_request_refresh()
