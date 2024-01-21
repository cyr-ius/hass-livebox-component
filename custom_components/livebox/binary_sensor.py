"""Livebox binary sensor entities."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any, Final

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MISSED_ICON
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiveboxBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Represents an Flow Sensor."""

    value_fn: Callable[..., Any] | None = None
    attrs: dict[str, Callable[..., Any]] | None = None


BINARYSENSOR_TYPES: Final[tuple[LiveboxBinarySensorEntityDescription, ...]] = (
    LiveboxBinarySensorEntityDescription(
        key="connectivity",
        name="WAN Status",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda x: x.get("wan_status", {}).get("WanState") == "Up",
        attrs={
            "link_type": lambda x: x.get("wan_status", {}).get("LinkType"),
            "link_state": lambda x: x.get("wan_status", {}).get("LinkState"),
            "last_connection_error": lambda x: x.get("wan_status", {}).get(
                "LastConnectionError"
            ),
            "wan_ipaddress": lambda x: x.get("wan_status", {}).get("IPAddress"),
            "wan_ipv6address": lambda x: x.get("wan_status", {}).get("IPv6Address"),
            "wan_ipv6prefix": lambda x: x.get("wan_status", {}).get(
                "IPv6DelegatedPrefix"
            ),
            "wired clients": lambda x: x.get("count_wired_devices"),
            "wireless clients": lambda x: x.get("count_wireless_devices"),
            "uptime": lambda x: datetime.today()
            - timedelta(seconds=x.get("infos", {}).get("UpTime", 0)),
        },
    ),
    LiveboxBinarySensorEntityDescription(
        key="callmissed",
        icon=MISSED_ICON,
        name="Call missed",
        value_fn=lambda x: len(x.get("cmissed", {}).get("call missed", [])) > 0,
        attrs={"missed_calls": lambda x: x.get("cmissed", [])},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Defer binary sensor setup to the shared sensor module."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        LiveboxBinarySensor(coordinator, description)
        for description in BINARYSENSOR_TYPES
    ]
    async_add_entities(entities, True)


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
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        attributes = {
            key: attr(self.coordinator.data)
            for key, attr in self.entity_description.attrs.items()
        }
        return attributes
