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
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfDataRate,
    UnitOfInformation,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LiveboxConfigEntry
from .const import DOWNLOAD_ICON, PHONE_ICON, UPLOAD_ICON
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity
from .helpers import find_item

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiveboxSensorEntityDescription(SensorEntityDescription):
    """Represents an Flow Sensor."""

    value_fn: Callable[..., Any] | None = None
    attrs: dict[str, Callable[..., Any]] | None = None


SENSOR_TYPES: Final[tuple[SensorEntityDescription, ...]] = (
    LiveboxSensorEntityDescription(
        key="down",
        name="xDSL Download",
        icon=DOWNLOAD_ICON,
        translation_key="down_rate",
        value_fn=lambda x: round(
            find_item(x, "dsl_status.DownstreamCurrRate", 0) / 1024, 2
        ),
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        attrs={
            "downstream_maxrate": lambda x: find_item(
                x, "dsl_status.DownstreamMaxRate"
            ),
            "downstream_lineattenuation": lambda x: find_item(
                x, "dsl_status.DownstreamLineAttenuation"
            ),
            "downstream_noisemargin": lambda x: find_item(
                x, "dsl_status.DownstreamNoiseMargin"
            ),
            "downstream_power": lambda x: find_item(x, "dsl_status.DownstreamPower"),
        },
    ),
    LiveboxSensorEntityDescription(
        key="up",
        name="xDSL Upload",
        icon=UPLOAD_ICON,
        translation_key="up_rate",
        value_fn=lambda x: round(
            x.get("dsl_status", {}).get("UpstreamCurrRate", 0) / 1024, 2
        ),
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        attrs={
            "upstream_maxrate": lambda x: find_item(x, "dsl_status.UpstreamMaxRate"),
            "upstream_lineattenuation": lambda x: find_item(
                x, "dsl_status.UpstreamLineAttenuation"
            ),
            "upstream_noisemargin": lambda x: find_item(
                x, "dsl_status.UpstreamNoiseMargin"
            ),
            "upstream_power": lambda x: find_item(x, "dsl_status.UpstreamPower"),
        },
    ),
    LiveboxSensorEntityDescription(
        key="wifi_rx",
        name="Wifi Rx",
        value_fn=lambda x: round(find_item(x, "wifi_stats.RxBytes", 0) / 1048576, 2),
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="wifi_rx",
        entity_registry_enabled_default=False,
    ),
    LiveboxSensorEntityDescription(
        key="wifi_tx",
        name="Wifi Tx",
        value_fn=lambda x: round(find_item(x, "wifi_stats.TxBytes", 0) / 1048576, 2),
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="wifi_tx",
        entity_registry_enabled_default=False,
    ),
    LiveboxSensorEntityDescription(
        key="fiber_power_rx",
        name="Fiber Power Rx",
        value_fn=lambda x: round(
            find_item(x, "fiber_status.SignalRxPower", 0) / 1000, 2
        ),
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="fiber_power_rx",
        attrs={
            "Downstream max rate Gbps": lambda x: find_item(
                x, "fiber_status.DownstreamMaxRate", 0
            )
            / 1000,
            "Downstream current rate Gbps": lambda x: find_item(
                x, "fiber_status.DownstreamCurrRate", 0
            )
            / 1000,
            "Max bitrate (Gbps)": lambda x: find_item(
                x, "fiber_status.MaxBitRateSupported", 0
            )
            / 1000,
            "Temperature (°C)": lambda x: find_item(x, "fiber_status.Temperature"),
            "Voltage (V)": lambda x: find_item(x, "fiber_status.Voltage"),
            "Bias (mA)": lambda x: find_item(x, "fiber_status.Bias"),
            "ONU State": lambda x: find_item(x, "fiber_status.ONUState"),
        },
    ),
    LiveboxSensorEntityDescription(
        key="fiber_power_tx",
        name="Fiber Power Tx",
        value_fn=lambda x: round(
            find_item(x, "fiber_status.SignalTxPower", 0) / 1000, 2
        ),
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="fiber_power_tx",
        attrs={
            "Upstream max rate (Gbps)": lambda x: find_item(
                x, "fiber_status.UpstreamMaxRate", 0
            )
            / 1000,
            "Upstream current rate (Gbps)": lambda x: find_item(
                x, "fiber_status.UpstreamCurrRate", 0
            )
            / 1000,
            "Max bitrate (Gbps)": lambda x: find_item(
                x, "fiber_status.MaxBitRateSupported", 0
            )
            / 1000,
            "Tx power (dbm)": lambda x: find_item(x, "fiber_status.SignalTxPower"),
            "Temperature (°C)": lambda x: find_item(x, "fiber_status.Temperature"),
            "Voltage (V)": lambda x: find_item(x, "fiber_status.Voltage"),
            "Bias (mA)": lambda x: find_item(x, "fiber_status.Bias"),
            "ONU State": lambda x: find_item(x, "fiber_status.ONUState"),
        },
    ),
    LiveboxSensorEntityDescription(
        key="fiber_tx",
        name="Fiber Tx",
        icon=UPLOAD_ICON,
        value_fn=lambda x: round(find_item(x, "fiber_stats.TxBytes", 0) / 1048576, 2),
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="fiber_tx",
        attrs={"Tx errors": lambda x: find_item(x, "fiber_stats.TxErrors")},
    ),
    LiveboxSensorEntityDescription(
        key="fiber_rx",
        name="Fiber Rx",
        icon=DOWNLOAD_ICON,
        value_fn=lambda x: round(find_item(x, "fiber_stats.RxBytes", 0) / 1048576, 2),
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="fiber_rx",
        attrs={"Rx errors": lambda x: find_item(x, "fiber_stats.RxErrors")},
    ),
    LiveboxSensorEntityDescription(
        key="callers",
        name="Callers",
        icon=PHONE_ICON,
        value_fn=lambda x: len(x.get("callers", {})),
        translation_key="callers",
        attrs={"callers": lambda x: x.get("callers")},
    ),
    LiveboxSensorEntityDescription(
        key="upnp",
        name="Ports forwarding",
        value_fn=lambda x: len(x.get("upnp", {})),
        translation_key="upnp",
        attrs={"Ports": lambda x: x.get("upnp")},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LiveboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    entities = []
    linktype = coordinator.data.get("wan_status", {}).get("LinkType", "").lower()

    for description in SENSOR_TYPES:
        if description.key in ["up", "down"] and linktype in ["gpon", "sfp"]:
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
