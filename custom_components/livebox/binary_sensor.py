"""Livebox binary sensor entities."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LiveboxConfigEntry
from .entity import LiveboxEntity
from .helpers import find_item

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class LiveboxBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Represents an Flow Sensor."""

    value_fn: Callable[..., Any]
    attrs: dict[str, Callable[..., Any]]
    index: int | None = None


BINARYSENSOR_TYPES: Final[tuple[LiveboxBinarySensorEntityDescription, ...]] = (
    LiveboxBinarySensorEntityDescription(
        key="connectivity",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda x: find_item(x, "wan_status.WanState", "").lower() == "up",
        attrs={
            "link_type": lambda x: find_item(x, "wan_status.LinkType"),
            "link_state": lambda x: find_item(x, "wan_status.LinkState"),
            "last_connection_error": lambda x: find_item(
                x, "wan_status.LastConnectionError"
            ),
            "wan_ipaddress": lambda x: find_item(x, "wan_status.IPAddress"),
            "wan_gw": lambda x: find_item(x, "wan_status.RemoteGateway"),
            "wan_ipv6address": lambda x: find_item(x, "wan_status.IPv6Address"),
            "wan_ipv6prefix": lambda x: find_item(x, "wan_status.IPv6DelegatedPrefix"),
            "wired clients": lambda x: x.get("count_wired_devices"),
            "wireless clients": lambda x: x.get("count_wireless_devices"),
        },
        translation_key="connectivity",
    ),
    LiveboxBinarySensorEntityDescription(
        key="callmissed",
        value_fn=lambda x: len(x.get("cmissed", [])) > 0,
        attrs={"missed_calls": lambda x: x.get("cmissed", [])},
        translation_key="callmissed",
    ),
    LiveboxBinarySensorEntityDescription(
        key="remote_access",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda x: x.get("remote_access"),
        attrs={},
        translation_key="remote_access",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LiveboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Defer binary sensor setup to the shared sensor module."""
    coordinator = entry.runtime_data
    entities = [
        LiveboxBinarySensor(coordinator, description)
        for description in BINARYSENSOR_TYPES
    ]

    for item in coordinator.data.get("ddns", []):
        idx = coordinator.data["ddns"].index(item)
        description = LiveboxBinarySensorEntityDescription(
            key=f"ddns_{idx}",
            index=idx,
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            value_fn=lambda x, y: (
                find_item(x, f"ddns.{y}.status", "").lower() != "updated"
            ),
            attrs={"last_update": lambda x, y: find_item(x, f"ddns.{y}.last_update")},
            translation_key="ddns",
            translation_placeholders={"service": str(item.get("service"))},
        )
        entities.append(LiveboxBinarySensor(coordinator, description))

    async_add_entities(entities)


class LiveboxBinarySensor(LiveboxEntity, BinarySensorEntity):
    """Livebox binary sensor."""

    entity_description: LiveboxBinarySensorEntityDescription

    @property
    def is_on(self) -> bool:
        """Return state."""
        description = self.entity_description
        if (idx := description.index) is not None:
            return bool(description.value_fn(self.coordinator.data, idx))
        return bool(description.value_fn(self.coordinator.data))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        description = self.entity_description
        attributes = {}
        for key, attr in description.attrs.items():
            if (idx := description.index) is not None:
                attributes.update({key: attr(self.coordinator.data, idx)})
            else:
                attributes.update({key: attr(self.coordinator.data)})
        return attributes
