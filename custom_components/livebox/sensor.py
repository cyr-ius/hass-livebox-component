"""Sensor for Livebox router."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfDataRate,
    UnitOfInformation,
)
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
        name="Wifi Rx",
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
        name="Wifi Tx",
        value_fn=lambda x: round(
            x.get("wifi_stats", {}).get("TxBytes", 0) / 1048576, 2
        ),
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="wifi_tx",
        entity_registry_enabled_default=False,
    ),
    LiveboxSensorEntityDescription(
        key="fiber_power_rx",
        name="Fiber Power Rx",
        value_fn=lambda x: x.get("fiber_status", {}).get("SignalRxPower"),
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="fiber_power_rx",
        attrs={
            "Downstream max rate": lambda x: x.get("fiber_status", {}).get(
                "DownstreamMaxRate"
            ),
            "Downstream current rate": lambda x: x.get("fiber_status", {}).get(
                "DownstreamCurrRate"
            ),
            "Max bitrate (gbps)": lambda x: x.get("fiber_status", {}).get(
                "MaxBitRateSupported", 0
            )
            / 1000,
            "Temperature": lambda x: x.get("fiber_status", {}).get("Temperature"),
            "Voltage": lambda x: x.get("fiber_status", {}).get("Voltage"),
            "Bias": lambda x: x.get("fiber_status", {}).get("Bias"),
            "ONU State": lambda x: x.get("fiber_status", {}).get("ONUState"),
        },
    ),
    LiveboxSensorEntityDescription(
        key="fiber_power_tx",
        name="Fiber Power Tx",
        value_fn=lambda x: x.get("fiber_status", {}).get("SignalTxPower", 0),
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="fiber_power_tx",
        attrs={
            "Upstream max rate": lambda x: x.get("fiber_status", {}).get(
                "UpstreamMaxRate"
            ),
            "Upstream current rate (mb)": lambda x: x.get("fiber_status", {}).get(
                "UpstreamCurrRate"
            ),
            "Max bitrate (gbps)": lambda x: x.get("fiber_status", {}).get(
                "MaxBitRateSupported", 0
            )
            / 1000,
            "Tx power (dbm)": lambda x: x.get("fiber_status", {}).get("SignalTxPower"),
            "Temperature": lambda x: x.get("fiber_status", {}).get("Temperature"),
            "Voltage": lambda x: x.get("fiber_status", {}).get("Voltage"),
            "Bias": lambda x: x.get("fiber_status", {}).get("Bias"),
            "ONU State": lambda x: x.get("fiber_status", {}).get("ONUState"),
        },
    ),
    LiveboxSensorEntityDescription(
        key="fiber_tx",
        name="Fiber Tx",
        value_fn=lambda x: round(
            x.get("fiber_stats", {}).get("TxBytes", 0) / 1048576, 2
        ),
        native_unit_of_measurement=UnitOfDataRate.MEGABYTES_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="fiber_tx",
        attrs={"Tx errors": lambda x: x.get("fiber_stats", {}).get("TxErrors")},
    ),
    LiveboxSensorEntityDescription(
        key="fiber_rx",
        name="Fiber Rx",
        value_fn=lambda x: round(
            x.get("fiber_stats", {}).get("RxBytes", 0) / 1048576, 2
        ),
        native_unit_of_measurement=UnitOfDataRate.MEGABYTES_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="fiber_rx",
        attrs={"Tx errors": lambda x: x.get("fiber_stats", {}).get("RxErrors")},
    ),
)

FIBER_MODE = ["fiber_power_rx", "fiber_power_tx", "fiber_rx", "fiber_tx"]
ADSL_MODE = ["up", "down"]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    wanmode = coordinator.data.get("nmc", {}).get("WanMode", "").upper()
    linktype = coordinator.data.get("wan_status", {}).get("LinkType", "").upper()

    for description in SENSOR_TYPES:
        if description.key in ADSL_MODE and "ETHERNET" in wanmode:
            continue
        if description.key in FIBER_MODE and "GPON" not in linktype:
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
