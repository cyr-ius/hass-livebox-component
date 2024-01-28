"""Sensor for Livebox router."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any, Final

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfDataRate, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DOWNLOAD_ICON, UPLOAD_ICON
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiveboxSensorEntityDescription(SensorEntityDescription):
    """Represents an Flow Sensor."""

    value_fn: Callable[..., Any] | None = None
    attrs: dict[str, Callable[..., Any]] | None = None


SENSOR_TYPES: Final[tuple[SensorEntityDescription, ...]] = (
    LiveboxSensorEntityDescription(
        key="down",
        name="Orange Livebox Download speed",
        icon=DOWNLOAD_ICON,
        translation_key="down_rate",
        value_fn=lambda x: round(
            x.get("dsl_status", {}).get("DownstreamCurrRate", 0) / 1024, 2
        ),
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        attrs={
            "downstream_maxrate": lambda x: x.get("dsl_status", {}).get(
                "DownstreamMaxRate"
            ),
            "downstream_lineattenuation": lambda x: x.get("", {}).get(
                "DownstreamLineAttenuation"
            ),
            "downstream_noisemargin": lambda x: x.get("dsl_status", {}).get(
                "DownstreamNoiseMargin"
            ),
            "downstream_power": lambda x: x.get("dsl_status", {}).get(
                "DownstreamPower"
            ),
        },
    ),
    LiveboxSensorEntityDescription(
        key="up",
        name="Orange Livebox Upload speed",
        icon=UPLOAD_ICON,
        translation_key="up_rate",
        value_fn=lambda x: round(
            x.get("dsl_status", {}).get("UpstreamCurrRate", 0) / 1024, 2
        ),
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        attrs={
            "upstream_maxrate": lambda x: x.get("dsl_status", {}).get(
                "UpstreamMaxRate"
            ),
            "upstream_lineattenuation": lambda x: x.get("dsl_status", {}).get(
                "UpstreamLineAttenuation"
            ),
            "upstream_noisemargin": lambda x: x.get("dsl_status", {}).get(
                "UpstreamNoiseMargin"
            ),
            "upstream_power": lambda x: x.get("dsl_status", {}).get("UpstreamPower"),
        },
    ),
    LiveboxSensorEntityDescription(
        key="wifi_rx",
        name="Wifif Rx",
        value_fn=lambda x: round(
            x.get("wifi_stats", {}).get("RxBytes", 0) / 1048576, 2
        ),
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="wifi_rx",
        entity_registry_enabled_default=False,
    ),
    LiveboxSensorEntityDescription(
        key="wifi_tx",
        name="Wifif Tx",
        value_fn=lambda x: round(
            x.get("wifi_stats", {}).get("TxBytes", 0) / 1048576, 2
        ),
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="wifi_tx",
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    wanmode = coordinator.data.get("nmc", {}).get("WanMode", "").upper()

    for description in SENSOR_TYPES:
        if description.key in ["up", "down"] and "ETHERNET" in wanmode:
            continue
        entities.append(LiveboxSensor(coordinator, description))

    async_add_entities(entities)


class LiveboxSensor(LiveboxEntity, SensorEntity):
    """Representation of a livebox sensor."""

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        description: LiveboxSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> float | None:
        """Return the native value of the device."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the device state attributes."""
        if self.entity_description.attrs:
            attributes = {
                key: attr(self.coordinator.data)
                for key, attr in self.entity_description.attrs.items()
            }
            return attributes
