"""Sensor for Livebox router."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final, cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LiveboxConfigEntry
from .const import DOMAIN, DOWNLOAD_ICON, PHONE_ICON, UPLOAD_ICON
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity
from .helpers import find_item

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class LiveboxSensorEntityDescription(SensorEntityDescription):
    """Represents an Flow Sensor."""

    value_fn: Callable[..., Any]
    attrs: dict[str, Callable[..., Any]] | None = None


@dataclass(frozen=True, kw_only=True)
class LiveboxDeviceSensorEntityDescription(SensorEntityDescription):
    """Represents a per-device sensor."""

    value_fn: Callable[..., Any]


def get_rolling_32_bit_value_fn(path: str) -> Callable[..., Any]:
    """Returns a closure function, that extracts a rolling 32-bit value from"""
    """the coordinator data structure, and tweaks its result so that HASS"""
    """properly accumulates the total rolling value."""
    """Meant for monotonically increasing counters: fiber/DSL Tx/Rx, and WiFi Tx/Rx"""

    previous_reading: int = 0
    previous_uptime: int = 0
    rolls: int = 0

    def value_fn(coordinator_data) -> int:
        nonlocal previous_reading
        nonlocal previous_uptime
        nonlocal rolls
        current_uptime = coordinator_data.get("infos", {}).get("UpTime") or 0
        current_reading = find_item(coordinator_data, path, 0)

        if current_uptime < previous_uptime:
            # The router has reset, so clear up previous counter value
            previous_reading = 0
            rolls = 0

        if current_reading < previous_reading:
            _LOGGER.debug("Rolling over 32-bit integer counter: %s", path)
            rolls += 1

        previous_reading = current_reading
        previous_uptime = current_uptime

        return (rolls << 32) + current_reading

    return value_fn


def get_closure_value_fn(path: str) -> Callable[..., Any]:
    """Returns a closure function for value_fn of entities with variable name"""
    return lambda x: find_item(x, path)


def kilobits_per_second_to_bits_per_second(value: Any) -> float:
    """Convert a Kbit/s API value to bit/s."""
    return value * 1000


def kilobits_per_second_to_gigabits_per_second(value: Any) -> float:
    """Convert a Kbit/s API value to Gbit/s."""
    return value / 1000000


def megabits_per_second_to_gigabits_per_second(value: Any) -> float:
    """Convert a Mbit/s API value to Gbit/s."""
    return value / 1000


def _normalize_device_key(device_key: str) -> str:
    """Return a stable entity key fragment for a device key."""
    return device_key.lower().replace(":", "_")


def _get_wireless_device_value_fn(
    device_key: str, path: str, default: Any = None
) -> Callable[..., Any]:
    """Return a sensor value function for a device field."""
    return lambda data: find_item(data, f"devices.{device_key}.{path}", default)


def _get_wireless_device_rate_value_fn(
    device_key: str, path: str
) -> Callable[..., Any]:
    """Return a bit/s sensor value function for a Kbit/s device rate field."""
    return lambda data: kilobits_per_second_to_bits_per_second(
        find_item(data, f"devices.{device_key}.{path}", 0)
    )


def _get_associated_wifi_device(
    coordinator_data: dict[str, Any], device_key: str
) -> dict[str, Any] | None:
    """Return the AP-side payload for a Wi-Fi client when available."""
    for lan_device in coordinator_data.get("lan", []):
        if lan_device.get("type") != "Wireless":
            continue
        associated_devices = lan_device.get("extra_attributes", {}).get(
            "associated_devices", {}
        )
        if not isinstance(associated_devices, dict):
            continue
        for associated_device in associated_devices.values():
            if not isinstance(associated_device, dict):
                continue
            if associated_device.get("MACAddress") == device_key:
                return associated_device
    return None


def _get_associated_wifi_metric_value_fn(
    device_key: str, metric: str, default: Any = None
) -> Callable[..., Any]:
    """Return a sensor value function for AP-side Wi-Fi statistics."""

    def value_fn(coordinator_data: dict[str, Any]) -> Any:
        associated_device = _get_associated_wifi_device(coordinator_data, device_key)
        if associated_device is None:
            return default
        value = associated_device.get(metric)
        return default if value is None else value

    return value_fn


def _is_wireless_device(device: dict[str, Any]) -> bool:
    """Return whether a Livebox device looks like a Wi-Fi client."""
    interface_name = device.get("InterfaceName", "")
    tags = device.get("Tags", "")
    return (
        isinstance(interface_name, str)
        and interface_name.startswith(("vap", "wlan", "wl"))
    ) or (isinstance(tags, str) and "wifi" in tags.split())


DEVICE_SENSOR_TYPES: Final[list[dict[str, Any]]] = [
    {
        "key": "downlink_rate",
        "name": "Downlink Rate",
        "icon": DOWNLOAD_ICON,
        "value_fn_factory": lambda device_key: _get_wireless_device_rate_value_fn(
            device_key, "LastDataDownlinkRate"
        ),
        "native_unit_of_measurement": UnitOfDataRate.BITS_PER_SECOND,
        "suggested_unit_of_measurement": UnitOfDataRate.MEGABITS_PER_SECOND,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.DATA_RATE,
    },
    {
        "key": "uplink_rate",
        "name": "Uplink Rate",
        "icon": UPLOAD_ICON,
        "value_fn_factory": lambda device_key: _get_wireless_device_rate_value_fn(
            device_key, "LastDataUplinkRate"
        ),
        "native_unit_of_measurement": UnitOfDataRate.BITS_PER_SECOND,
        "suggested_unit_of_measurement": UnitOfDataRate.MEGABITS_PER_SECOND,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.DATA_RATE,
    },
    {
        "key": "tx_bytes",
        "name": "Tx Bytes",
        "icon": UPLOAD_ICON,
        "value_fn_factory": lambda device_key: _get_associated_wifi_metric_value_fn(
            device_key, "TxBytes", 0
        ),
        "native_unit_of_measurement": UnitOfInformation.BYTES,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "device_class": SensorDeviceClass.DATA_SIZE,
    },
    {
        "key": "rx_bytes",
        "name": "Rx Bytes",
        "icon": DOWNLOAD_ICON,
        "value_fn_factory": lambda device_key: _get_associated_wifi_metric_value_fn(
            device_key, "RxBytes", 0
        ),
        "native_unit_of_measurement": UnitOfInformation.BYTES,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "device_class": SensorDeviceClass.DATA_SIZE,
    },
    {
        "key": "signal_strength",
        "name": "Signal Strength",
        "value_fn_factory": lambda device_key: _get_wireless_device_value_fn(
            device_key, "SignalStrength", None
        ),
        "native_unit_of_measurement": SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
    },
    {
        "key": "signal_noise_ratio",
        "name": "Signal Noise Ratio",
        "value_fn_factory": lambda device_key: _get_wireless_device_value_fn(
            device_key, "SignalNoiseRatio", None
        ),
        "native_unit_of_measurement": "dB",
        "state_class": SensorStateClass.MEASUREMENT,
    },
]


SENSOR_TYPES: Final[list[LiveboxSensorEntityDescription]] = [
    LiveboxSensorEntityDescription(
        key="down",
        name="xDSL Download",
        icon=DOWNLOAD_ICON,
        translation_key="down_rate",
        value_fn=lambda x: find_item(x, "dsl_status.DownstreamCurrRate", 0),
        native_unit_of_measurement=UnitOfDataRate.KILOBITS_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DATA_RATE,
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
        value_fn=lambda x: x.get("dsl_status", {}).get("UpstreamCurrRate", 0),
        native_unit_of_measurement=UnitOfDataRate.KILOBITS_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DATA_RATE,
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
        icon="mdi:wifi-arrow-down",
        value_fn=get_rolling_32_bit_value_fn("wifi_stats.RxBytes"),
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DATA_SIZE,
        translation_key="wifi_rx",
        entity_registry_enabled_default=False,
    ),
    LiveboxSensorEntityDescription(
        key="wifi_tx",
        name="Wifi Tx",
        icon="mdi:wifi-arrow-up",
        value_fn=get_rolling_32_bit_value_fn("wifi_stats.TxBytes"),
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DATA_SIZE,
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
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        translation_key="fiber_power_rx",
        attrs={
            "Downstream max rate Gbps": lambda x: (
                kilobits_per_second_to_gigabits_per_second(
                    find_item(x, "fiber_status.DownstreamMaxRate", 0)
                )
            ),
            "Downstream current rate Gbps": lambda x: (
                kilobits_per_second_to_gigabits_per_second(
                    find_item(x, "fiber_status.DownstreamCurrRate", 0)
                )
            ),
            "Max bitrate (Gbps)": lambda x: megabits_per_second_to_gigabits_per_second(
                find_item(x, "fiber_status.MaxBitRateSupported", 0)
            ),
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
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        translation_key="fiber_power_tx",
        attrs={
            "Upstream max rate (Gbps)": lambda x: (
                kilobits_per_second_to_gigabits_per_second(
                    find_item(x, "fiber_status.UpstreamMaxRate", 0)
                )
            ),
            "Upstream current rate (Gbps)": lambda x: (
                kilobits_per_second_to_gigabits_per_second(
                    find_item(x, "fiber_status.UpstreamCurrRate", 0)
                )
            ),
            "Max bitrate (Gbps)": lambda x: megabits_per_second_to_gigabits_per_second(
                find_item(x, "fiber_status.MaxBitRateSupported", 0)
            ),
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
        value_fn=get_rolling_32_bit_value_fn("fiber_stats.TxBytes"),
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DATA_SIZE,
        translation_key="fiber_tx",
        attrs={"Tx errors": lambda x: find_item(x, "fiber_stats.TxErrors")},
    ),
    LiveboxSensorEntityDescription(
        key="fiber_rx",
        name="Fiber Rx",
        icon=DOWNLOAD_ICON,
        value_fn=get_rolling_32_bit_value_fn("fiber_stats.RxBytes"),
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DATA_SIZE,
        translation_key="fiber_rx",
        attrs={"Rx errors": lambda x: find_item(x, "fiber_stats.RxErrors")},
    ),
    LiveboxSensorEntityDescription(
        key="callers",
        name="Callers",
        icon=PHONE_ICON,
        value_fn=lambda x: len(x.get("callers", {})),
        state_class=SensorStateClass.TOTAL,
        translation_key="callers",
        attrs={"callers": lambda x: x.get("callers")},
    ),
    LiveboxSensorEntityDescription(
        key="upnp",
        name="Ports forwarding",
        value_fn=lambda x: len(x.get("upnp", {})),
        state_class=SensorStateClass.TOTAL,
        translation_key="upnp",
        attrs={"Ports": lambda x: x.get("upnp")},
        entity_registry_enabled_default=False,
    ),
    LiveboxSensorEntityDescription(
        key="dhcp_leases",
        name="DHCP Leases",
        value_fn=lambda x: len(x.get("dhcp_leases", {})),
        state_class=SensorStateClass.TOTAL,
        translation_key="dhcp_leases",
        attrs={"Leases": lambda x: x.get("dhcp_leases")},
        entity_registry_enabled_default=False,
    ),
    LiveboxSensorEntityDescription(
        key="guest_dhcp_leases",
        name="Guest DHCP Leases",
        value_fn=lambda x: len(x.get("guest_dhcp_leases", {})),
        state_class=SensorStateClass.TOTAL,
        translation_key="guest_dhcp_leases",
        attrs={"Leases": lambda x: x.get("guest_dhcp_leases")},
        entity_registry_enabled_default=False,
    ),
    LiveboxSensorEntityDescription(
        key="uptime",
        name="Uptime",
        icon="progress-clock",
        value_fn=lambda x: find_item(x, "infos.UpTime", 0),
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.DURATION,
        translation_key="uptime",
        entity_registry_enabled_default=False,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LiveboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    entities = []
    tracked = set()
    linktype = coordinator.data.get("wan_status", {}).get("LinkType", "").lower()

    sensor_stats = []
    for name, item in coordinator.data.get("stats", {}).items():
        sensor_stats.append(
            LiveboxSensorEntityDescription(
                key=f"{name}_rate_rx",
                name=f"{item['friendly_name']} Rate Rx",
                value_fn=get_closure_value_fn(f"stats.{name}.rate_rx"),
                translation_key=f"{name}_rate_rx",
                native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                state_class=SensorStateClass.MEASUREMENT,
                device_class=SensorDeviceClass.DATA_RATE,
            )
        )
        sensor_stats.append(
            LiveboxSensorEntityDescription(
                key=f"{name}_rate_tx",
                name=f"{item['friendly_name']} Rate Tx",
                value_fn=get_closure_value_fn(f"stats.{name}.rate_tx"),
                translation_key=f"{name}_rate_tx",
                native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                state_class=SensorStateClass.MEASUREMENT,
                device_class=SensorDeviceClass.DATA_RATE,
            )
        )

    for description in SENSOR_TYPES + sensor_stats:
        if description.key in ["up", "down"] and linktype in ["gpon", "sfp"]:
            continue
        entities.append(LiveboxSensor(coordinator, description))

    @callback
    def _async_update_device_sensors() -> None:
        """Add per-device sensors when new devices appear."""
        async_add_new_device_entities(coordinator, async_add_entities, tracked)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            coordinator.signal_device_new,
            _async_update_device_sensors,
        )
    )

    _async_update_device_sensors()
    async_add_entities(entities)


@callback
def async_add_new_device_entities(
    coordinator: LiveboxDataUpdateCoordinator,
    async_add_entities: AddEntitiesCallback,
    tracked: set[str],
) -> None:
    """Add per-device sensor entities from the router."""
    new_entities = []

    for device_key, device in coordinator.data.get("devices", {}).items():
        if not _is_wireless_device(device):
            continue
        device_name = device.get("Name") or device_key
        device_key_fragment = _normalize_device_key(device_key)

        for template in DEVICE_SENSOR_TYPES:
            entity_key = f"{device_key_fragment}_{template['key']}"
            if entity_key in tracked:
                continue

            description = LiveboxDeviceSensorEntityDescription(
                key=entity_key,
                name=template["name"],
                icon=template.get("icon"),
                value_fn=template["value_fn_factory"](device_key),
                native_unit_of_measurement=template.get("native_unit_of_measurement"),
                suggested_unit_of_measurement=template.get(
                    "suggested_unit_of_measurement"
                ),
                state_class=template.get("state_class"),
                device_class=template.get("device_class"),
                entity_category=EntityCategory.DIAGNOSTIC,
                entity_registry_enabled_default=False,
            )
            new_entities.append(
                LiveboxDeviceSensor(
                    coordinator,
                    description,
                    device_key=device_key,
                    device_name=device_name,
                )
            )
            tracked.add(entity_key)

    if new_entities:
        async_add_entities(new_entities)


class LiveboxSensor(LiveboxEntity, SensorEntity):  # pyrefly: ignore[inconsistent-inheritance]
    """Representation of a livebox sensor."""

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> float | None:
        """Return the native value of the device."""
        description = cast(LiveboxSensorEntityDescription, self.entity_description)
        return description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the device state attributes."""
        description = cast(LiveboxSensorEntityDescription, self.entity_description)
        if description.attrs:
            return {
                key: attr(self.coordinator.data)
                for key, attr in description.attrs.items()
            }
        return None


class LiveboxDeviceSensor(
    LiveboxSensor,
):  # pyrefly: ignore[inconsistent-inheritance]
    """Representation of a per-device sensor."""

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        description: LiveboxDeviceSensorEntityDescription,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)
        self._device_key = device_key
        self._device_name = device_name
        self._via_device = coordinator.get_parent_device_identifier(self._device_key)

    @property
    def native_value(self) -> float | int | None:
        """Return the native value of the device."""
        description = cast(
            LiveboxDeviceSensorEntityDescription,
            self.entity_description,
        )
        return description.value_fn(self.coordinator.data)

    @property
    def device_info(self) -> DeviceInfo | None:  # pyrefly: ignore
        """Return device info to link the sensor to the Livebox device."""
        return DeviceInfo(
            name=self._device_name,
            identifiers={(DOMAIN, self._device_key)},
        )
