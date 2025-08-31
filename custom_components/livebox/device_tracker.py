"""Support for the Livebox platform."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)

from . import LiveboxConfigEntry
from .const import CONF_TRACKING_TIMEOUT, DEFAULT_TRACKING_TIMEOUT, DOMAIN
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LiveboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up device tracker from config entry."""
    coordinator = entry.runtime_data
    tracked = set()

    @callback
    def async_update_router() -> None:
        """Update the values of the router."""
        async_add_new_tracked_entities(coordinator, async_add_entities, tracked)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, coordinator.signal_device_new, async_update_router
        )
    )

    async_update_router()


@callback
def async_add_new_tracked_entities(
    coordinator: LiveboxDataUpdateCoordinator,
    async_add_entities: AddConfigEntryEntitiesCallback,
    tracked: set[str],
) -> None:
    """Add new tracker entities from the router."""
    new_tracked = []

    _LOGGER.debug("Adding device trackers entities")
    for mac, device in coordinator.data.get("devices", {}).items():
        if mac in tracked:
            continue
        _LOGGER.debug("New device tracker: %s", device.get("Name", "Unknown"))
        new_tracked.append(
            LiveboxDeviceScannerEntity(
                coordinator,
                EntityDescription(key=f"{mac}_tracker", name=device.get("Name")),
                device,
            )
        )
        tracked.add(mac)

    async_add_entities(new_tracked)


@callback
class LiveboxDeviceScannerEntity(LiveboxEntity, ScannerEntity):
    """Represent a tracked device."""

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        description: EntityDescription,
        device: dict[str, Any],
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator, description)
        self.coordinator = coordinator
        self.entity_description = description

        self._device = device
        self._old_status = datetime.today()
        self._attr_is_connected = device.get("Active", False)
        self._attr_source_type = SourceType.ROUTER
        self._attr_mac_address = device.get("Key")
        self._attr_ip_address = device.get("IPAddress")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        attrs = {
            "interface_name": self._device.get("InterfaceName"),
            "type": self._device.get("DeviceType"),
            "vendor": self._device.get("VendorClassID"),
            "manufacturer": self._device.get("Manufacturer"),
            "first_seen": self._device.get("FirstSeen"),
            "last_connection": self._device.get("LastConnection"),
            "last_changed": self._device.get("LastChanged"),
        }

        if self._device.get("InterfaceName") in [
            "eth1",
            "eth2",
            "eth3",
            "eth4",
            "eth5",
        ]:
            attrs.update({"connection": "ethernet", "band": "Wired"})

        if (iname := self._device.get("InterfaceName")) in [
            "eth6",
            "wlan0",
            "wl0",
            "wlguest2",
            "wlguest5",
        ]:
            match self._device.get("SignalStrength", 0) * -1:
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
                    "band": self._device.get("OperatingFrequencyBand"),
                    "signal_strength": self._device.get("SignalStrength"),
                    "signal_quality": signal_quality,
                    "frenquency_band": self._device.get("OperatingFrequencyBand"),
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
            case "Access Point":
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
            case "Nas":
                return "mdi:nas"
            case _:
                return "mdi:devices"

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected to the network via router."""
        return self._attr_is_connected

    @property
    def device_info(self):
        """Return device info to link entity to the Livebox device."""
        return {
            "name": self._unique_name,
            "identifiers": {(DOMAIN, self._device.get("Key"))},
            "via_device": (DOMAIN, self.coordinator.unique_id),
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Respond to a DataUpdateCoordinator update."""
        device = self.coordinator.data.get("devices", {}).get(self.unique_id, {})
        self._attr_ip_address = device.get("IPAddress")

        timeout_tracking = self.coordinator.config_entry.options.get(
            CONF_TRACKING_TIMEOUT, DEFAULT_TRACKING_TIMEOUT
        )
        self._attr_is_connected = device.get("Active", False)
        if self._attr_is_connected is True:
            self._old_status = datetime.today() + timedelta(seconds=timeout_tracking)
        if self._attr_is_connected is False and self._old_status > datetime.today():
            _LOGGER.debug("%s will be disconnected at %s", self.name, self._old_status)
            self._attr_is_connected = True

        _LOGGER.debug("%s is connected: %s", self.name, self._attr_is_connected)
        self.async_write_ha_state()
