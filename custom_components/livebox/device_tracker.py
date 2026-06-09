"""Support for the Livebox platform."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, cast

from homeassistant.components.device_tracker import ScannerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LiveboxConfigEntry
from .const import CONF_TRACKING_TIMEOUT, DEFAULT_TRACKING_TIMEOUT, DOMAIN
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity

_LOGGER = logging.getLogger(__name__)

# Left side = Home Assistant attribute names, right side = raw Livebox keys.
_BASE_DEVICE_ATTRIBUTE_FIELDS: dict[str, str] = {
    "interface_name": "InterfaceName",
    "type": "DeviceType",
    "vendor": "VendorClassID",
    "manufacturer": "Manufacturer",
    "first_seen": "FirstSeen",
    "last_connection": "LastConnection",
    "last_changed": "LastChanged",
}

# Left side = Home Assistant attribute names, right side = raw Livebox keys.
_WIRELESS_DEVICE_ATTRIBUTE_FIELDS: dict[str, str] = {
    "frequency_band": "OperatingFrequencyBand",
}


def _is_wireless_device(device: dict[str, Any]) -> bool:
    """Return whether a Livebox device looks like a Wi-Fi client."""
    interface_name = device.get("InterfaceName", "")
    tags = device.get("Tags", "")
    return (
        isinstance(interface_name, str)
        and interface_name.startswith(("vap", "wlan", "wl"))
    ) or (isinstance(tags, str) and "wifi" in tags.split())


def _copy_selected_fields(
    source: dict[str, Any], fields: dict[str, str]
) -> dict[str, Any]:
    """Return non-empty values from a raw Livebox payload using normalized names."""
    return {
        attr: value
        for attr, key in fields.items()
        if (value := source.get(key)) is not None and value != ""
    }


def _get_signal_quality(signal_strength: Any) -> str:
    """Return a human-readable signal quality from the raw signal strength."""
    if not isinstance(signal_strength, (int, float)):
        return "unknown"

    match signal_strength * -1:
        case x if x > 90:
            return "very bad"
        case x if 80 <= x < 90:
            return "bad"
        case x if 70 <= x < 80:
            return "very low"
        case x if 67 <= x < 70:
            return "low"
        case x if 60 <= x < 67:
            return "good"
        case x if 50 <= x < 60:
            return "very good"
        case x if 30 <= x < 50:
            return "excellent"
        case _:
            return "unknown"


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
    async_add_entities: AddEntitiesCallback,
    tracked: set[str],
) -> None:
    """Add new tracker entities from the router."""
    repeater_entities = []
    client_entities = []
    repeater_keys = coordinator.data.get("topology_repeaters", {})

    _LOGGER.debug("Adding device trackers entities")
    for mac, device in coordinator.data.get("devices", {}).items():
        if mac in tracked:
            continue
        _LOGGER.debug("New device tracker: %s", device.get("Name", "Unknown"))
        entity = LiveboxDeviceScannerEntity(
            coordinator,
            EntityDescription(key=f"{mac}_tracker", name=device.get("Name")),
            device,
        )
        if mac in repeater_keys:
            repeater_entities.append(entity)
        else:
            client_entities.append(entity)
        tracked.add(mac)

    async_add_entities(repeater_entities + client_entities)


@callback
class LiveboxDeviceScannerEntity(  # pyrefly: ignore[inconsistent-inheritance]
    LiveboxEntity, ScannerEntity
):
    """Represent a tracked device."""

    _attr_name = None

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        description: EntityDescription,
        device: dict[str, Any],
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator, description)
        self._device = device
        self._device_key = cast(str | None, device.get("Key"))
        self._via_device = coordinator.get_parent_device_identifier(self._device_key)
        self._old_status = datetime.today()
        self._attr_is_connected = device.get("Active", False)
        self._attr_source_type = SourceType.ROUTER
        self._attr_mac_address = self._device_key
        self._attr_ip_address = device.get("IPAddress")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        attrs = _copy_selected_fields(self._device, _BASE_DEVICE_ATTRIBUTE_FIELDS)

        if self._device.get("InterfaceName") in [
            "eth1",
            "eth2",
            "eth3",
            "eth4",
            "eth5",
        ]:
            attrs.update({"connection": "ethernet", "frequency_band": "Wired"})

        if _is_wireless_device(self._device):
            iname = self._device.get("InterfaceName")
            signal_quality = _get_signal_quality(self._device.get("SignalStrength"))
            attrs.update(
                {
                    "frequency_band": self._device.get("OperatingFrequencyBand"),
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
        timeout_tracking = self.coordinator.config_entry.options.get(
            CONF_TRACKING_TIMEOUT, DEFAULT_TRACKING_TIMEOUT
        )
        status = self._device.get("Active", False)
        if status is True:
            self._old_status = datetime.today() + timedelta(seconds=timeout_tracking)
        if status is False and self._old_status > datetime.today():
            _LOGGER.debug("%s will be disconnected at %s", self.name, self._old_status)
            return True
        _LOGGER.debug("Is Connected: %s", status)
        return status

    @property
    def device_info(self) -> DeviceInfo | None:  # pyrefly: ignore
        """Return device info to link entity to the Livebox device."""
        if isinstance(self._device_key, str):
            device_identifier = self._device_key
        elif isinstance(self.name, str):
            device_identifier = self.name
        else:
            device_identifier = DOMAIN
        return DeviceInfo(
            name=self._device.get("Name"),
            identifiers={(DOMAIN, device_identifier)},
            via_device=self._via_device,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Respond to a DataUpdateCoordinator update."""
        self._device = self.coordinator.data.get("devices", {}).get(
            self._device_key, {}
        )
        self._attr_ip_address = self._device.get("IPAddress")
        via_device = self.coordinator.get_parent_device_identifier(self._device_key)
        if via_device != self._via_device and self.device_entry is not None:
            # Re-link the existing device when topology becomes available later.
            self._via_device = via_device
            self.device_entry = dr.async_get(self.hass).async_get_or_create(
                config_entry_id=self.coordinator.config_entry.entry_id,
                **cast(DeviceInfo, self.device_info),
            )
        else:
            self._via_device = via_device

        self.async_write_ha_state()
