"""Sensor for Livebox router."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Final

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfDataRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DOWNLOAD_ICON, UPLOAD_ICON
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FlowSensorEntityDescription(SensorEntityDescription):
    """Represents an Flow Sensor."""

    current_rate: str | None = None
    attr: dict | None = None


SENSOR_TYPES: Final[tuple[SensorEntityDescription, ...]] = (
    FlowSensorEntityDescription(
        key="down",
        name="Orange Livebox Download speed",
        icon=DOWNLOAD_ICON,
        translation_key="down_rate",
        current_rate="DownstreamCurrRate",
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
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
        icon=UPLOAD_ICON,
        translation_key="up_rate",
        current_rate="UpstreamCurrRate",
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        attr={
            "upstream_maxrate": "UpstreamMaxRate",
            "upstream_lineattenuation": "UpstreamLineAttenuation",
            "upstream_noisemargin": "UpstreamNoiseMargin",
            "upstream_power": "UpstreamPower",
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [FlowSensor(coordinator, description) for description in SENSOR_TYPES]

    nmc = coordinator.data.get("nmc", {})
    if nmc.get("WanMode") and "ETHERNET" not in nmc["WanMode"].upper():
        async_add_entities(entities, True)


class FlowSensor(LiveboxEntity, SensorEntity):
    """Representation of a livebox sensor."""

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> float | None:
        """Return the native value of the device."""
        current_rate = self.entity_description.current_rate
        if val_rate := self.coordinator.data["dsl_status"].get(current_rate):
            return round(val_rate / 1000, 2)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the device state attributes."""
        attributes = {}
        for key, value in self.entity_description.attr.items():
            attributes[key] = self.coordinator.data["dsl_status"].get(value)
        return attributes
