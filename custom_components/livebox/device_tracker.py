"""Support for the Livebox platform."""
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TRACKING_TIMEOUT, DEFAULT_TRACKING_TIMEOUT, DOMAIN
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up device tracker from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        LiveboxDeviceScannerEntity(
            coordinator, SensorEntityDescription(key=f"{uid}_tracker"), device
        )
        for uid, device in coordinator.data.get("devices", {}).items()
        if "IPAddress" and "PhysAddress" in device
    ]
    async_add_entities(entities, True)


class LiveboxDeviceScannerEntity(LiveboxEntity, ScannerEntity):
    """Represent a tracked device."""

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        description: SensorEntityDescription,
        device: dict[str, Any],
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator, description)
        self._device = device
        self._old_status = datetime.today()
        self._attr_name = device.get("Name")
        self._attr_unique_id = device.get("Key")
        self._attr_device_info = {
            "name": device.get("Name"),
            "identifiers": {(DOMAIN, device.get("Key"))},
            "via_device": (DOMAIN, coordinator.unique_id),
        }

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected to the network."""
        timeout_tracking = self.coordinator.config_entry.options.get(
            CONF_TRACKING_TIMEOUT, DEFAULT_TRACKING_TIMEOUT
        )
        device = self.coordinator.data.get("devices", {}).get(self.unique_id, {})
        status = device.get("Active", False)
        if status is True:
            self._old_status = datetime.today() + timedelta(seconds=timeout_tracking)
        if status is False and self._old_status > datetime.today():
            _LOGGER.debug("%s will be disconnected at %s", self.name, self._old_status)
            return True

        return status

    @property
    def source_type(self) -> SourceType:
        """Return the source type, eg gps or router, of the device."""
        return SourceType.ROUTER

    @property
    def ip_address(self) -> str:
        """Return ip address."""
        return self._device.get("IPAddress")

    @property
    def mac_address(self) -> str:
        """Return mac address."""
        return self._device.get("Key")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        device = self.coordinator.data.get("devices", {}).get(self.unique_id, {})
        attrs = {
            "interface_name": device.get("InterfaceName"),
            "type": device.get("DeviceType"),
            "vendor": device.get("VendorClassID"),
            "manufacturer": device.get("Manufacturer"),
            "first_seen": device.get("FirstSeen"),
            "last_connection": device.get("LastConnection"),
            "last_changed": device.get("LastChanged"),
        }

        if device.get("InterfaceName") in [
            "eth1",
            "eth2",
            "eth3",
            "eth4",
            "eth5",
        ]:
            attrs.update({"connection": "ethernet", "band": "Wired"})

        if (iname := device.get("InterfaceName")) in [
            "eth6",
            "wlan0",
            "wl0",
            "wlguest2",
            "wlguest5",
        ]:
            match device.get("SignalStrength", 0) * -1:
                case x if x > 90:
                    signal_quality = "very bad"
                case x if 80 <= x < 90:
                    signal_quality = "bad"
                case x if 70 <= x < 80:
                    signal_quality = "very low"
                case x if 67 <= x < 70:
                    signal_quality = "low"
                case x if 60 <= x < 67:
                    signal_quality = "good"
                case x if 50 <= x < 60:
                    signal_quality = "very good"
                case x if 30 <= x < 50:
                    signal_quality = "excellent"
                case _:
                    signal_quality = "unknown"
            attrs.update(
                {
                    "is_wireless": True,
                    "band": self._device.get("OperatingFrequencyBand"),
                    "signal_strength": self._device.get("SignalStrength"),
                    "signal_quality": signal_quality,
                    "connection": "wifi"
                    if iname not in ["wlguest2", "wlguest5"]
                    else "guestwifi",
                }
            )

        return attrs

    @property
    def icon(self) -> str:
        """Return icon."""
        match self._device.get("DeviceType"):
            case "Computer" | "Desktop iOS" | "Desktop Windows" | "Desktop Linux":
                return "mdi:desktop-tower-monitor"
            case "Laptop" | "Laptop iOS" | "Laptop Windows" | "Laptop Linux":
                return "mdi:laptop"
            case "Switch4" | "Switch8" | "Switch":
                return "mdi:switch"
            case "Acces Point":
                return "mdi:access-point-network"
            case "TV" | "TVKey" | "Apple TV":
                return "mdi:television"
            case "HomePlug":
                return "mdi:network"
            case "Printer":
                return "mdi:printer"
            case "Set-top Box TV UHD" | "Set-top Box":
                return "mdi:dlna"
            case "Mobile iOS" | "Mobile" | "Mobile Android":
                return "mdi:cellphone"
            case "Tablet iOS" | "Tablet" | "Tablet Android" | "Tablet Windows":
                return "mdi:cellphone"
            case "Game Console":
                return "mdi:gamepad-square"
            case "Homepoint":
                return "mdi:home-automation"
            case _:
                return "mdi:devices"
