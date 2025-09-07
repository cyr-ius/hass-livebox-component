"""Livebox binary sensor entities."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Final

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LiveboxConfigEntry
from .const import DDNS_ICON, MISSED_ICON, RA_ICON
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity
from .helpers import find_item

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiveboxBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Represents an Flow Sensor."""

    value_fn: Callable[..., Any] | None = None
    attrs: dict[str, Callable[..., Any]] | None = None
    index: int | None = None


BINARYSENSOR_TYPES: Final[tuple[LiveboxBinarySensorEntityDescription, ...]] = (
    LiveboxBinarySensorEntityDescription(
        key="connectivity",
        name="WAN Status",
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
            "wan_ipv6address": lambda x: find_item(x, "wan_status.IPv6Address"),
            "wan_ipv6prefix": lambda x: find_item(x, "wan_status.IPv6DelegatedPrefix"),
            "wired clients": lambda x: x.get("count_wired_devices"),
            "wireless clients": lambda x: x.get("count_wireless_devices"),
            "uptime": lambda x: datetime.today()
            - timedelta(seconds=find_item(x, "infos.UpTime", 0)),
        },
        translation_key="connectivity",
    ),
    LiveboxBinarySensorEntityDescription(
        key="callmissed",
        icon=MISSED_ICON,
        name="Call missed",
        value_fn=lambda x: len(x.get("cmissed", [])) > 0,
        attrs={"missed_calls": lambda x: x.get("cmissed", [])},
        translation_key="callmissed",
    ),
    LiveboxBinarySensorEntityDescription(
        key="remote_access",
        name="Remote Access",
        icon=RA_ICON,
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
            icon=DDNS_ICON,
            device_class=BinarySensorDeviceClass.PROBLEM,
            name=f"Dynamic DNS ({item.get('service')})",
            value_fn=lambda x, y: find_item(x, f"ddns.{y}.status", "").lower()
            != "updated",
            attrs={"last_update": lambda x, y: find_item(x, f"ddns.{y}.last_update")},
            translation_key=f"ddns_{idx}",
        )
        entities.append(LiveboxBinarySensor(coordinator, description))

    async_add_entities(entities)


class LiveboxBinarySensor(LiveboxEntity, BinarySensorEntity):
    """Livebox binary sensor."""

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        description: LiveboxBinarySensorEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description)

    @property
    def is_on(self) -> bool:
        """Return state."""
        if (idx := self.entity_description.index) is not None:
            return self.entity_description.value_fn(self.coordinator.data, idx)
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        attributes = {}
        for key, attr in self.entity_description.attrs.items():
            if (idx := self.entity_description.index) is not None:
                attributes.update({key: attr(self.coordinator.data, idx)})
            else:
                attributes.update({key: attr(self.coordinator.data)})
        return attributes
