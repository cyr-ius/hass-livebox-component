"""Constants for the Livebox component."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from homeassistant.const import DATA_RATE_MEGABITS_PER_SECOND
from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    SensorEntityDescription,
)

DOMAIN = "livebox"
COORDINATOR = "coordinator"
UNSUB_LISTENER = "unsubscribe_listener"
LIVEBOX_ID = "id"
LIVEBOX_API = "api"
PLATFORMS = ["sensor", "binary_sensor", "device_tracker", "switch", "button"]

TEMPLATE_SENSOR = "Orange Livebox"

DEFAULT_USERNAME = "admin"
DEFAULT_HOST = "192.168.1.1"
DEFAULT_PORT = 80

CALLID = "callId"

CONF_LAN_TRACKING = "lan_tracking"
DEFAULT_LAN_TRACKING = False

CONF_TRACKING_TIMEOUT = "timeout_tracking"
DEFAULT_TRACKING_TIMEOUT = 300

UPLOAD_ICON = "mdi:upload-network"
DOWNLOAD_ICON = "mdi:download-network"
MISSED_ICON = "mdi:phone-alert"
RESTART_ICON = "mdi:restart-alert"
RING_ICON = "mdi:phone-classic"


@dataclass
class FlowSensorEntityDescription(SensorEntityDescription):
    """Represents an Flow Sensor."""

    current_rate: str | None = None
    attr: dict | None = None


SENSOR_TYPES: Final[tuple[SensorEntityDescription, ...]] = (
    FlowSensorEntityDescription(
        key="down",
        name="Orange Livebox Download speed",
        icon=DOWNLOAD_ICON,
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
        icon=UPLOAD_ICON,
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
