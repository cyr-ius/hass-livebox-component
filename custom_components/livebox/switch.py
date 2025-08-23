"""Sensor for Livebox router."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LiveboxConfigEntry
from .const import DEVICE_WANACCESS_ICON, DOMAIN, GUESTWIFI_ICON
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiveboxSwitchEntityDescription(SwitchEntityDescription):
    """Class describing Livebox button entities."""

    value_fn: Callable[..., Any] | None = None
    turn_on_parameters: dict[str, Any] | None = None
    turn_off_parameters: dict[str, Any] | None = None


SWITCH_TYPES: Final[tuple[SwitchEntityDescription, ...]] = (
    LiveboxSwitchEntityDescription(
        key="wifi",
        name="Wifi switch",
        translation_key="wifi_switch",
        value_fn=lambda x: getattr(getattr(x, "nmc"), "async_set_wifi"),
        turn_on_parameters={"Enable": "true", "Status": "true"},
        turn_off_parameters={"Enable": "false", "Status": "false"},
    ),
    LiveboxSwitchEntityDescription(
        key="guest_wifi",
        name="Guest Wifi switch",
        icon=GUESTWIFI_ICON,
        translation_key="guest_wifi",
        value_fn=lambda x: getattr(getattr(x, "nmc"), "async_set_guest_wifi"),
        turn_on_parameters={"Enable": "true", "Status": "true"},
        turn_off_parameters={"Enable": "false", "Status": "false"},
    ),
)

SWITCH_TYPES_5: Final[tuple[SwitchEntityDescription, ...]] = (
    LiveboxSwitchEntityDescription(
        key="wifi",
        name="Wifi switch",
        translation_key="wifi_switch",
        value_fn=lambda x: getattr(getattr(x, "nemo"), "async_set_wlan_config"),
        turn_on_parameters={
            "mibs": {
                "penable": {
                    "wl0": {"Enable": True, "PersistentEnable": True, "Status": True},
                    "eth4": {"Enable": True, "PersistentEnable": True, "Status": True},
                    "wlanvap": {"wl0": {}, "eth4": {}},
                }
            }
        },
        turn_off_parameters={
            "mibs": {
                "penable": {
                    "wl0": {
                        "Enable": False,
                        "PersistentEnable": False,
                        "Status": False,
                    },
                    "eth4": {
                        "Enable": False,
                        "PersistentEnable": False,
                        "Status": False,
                    },
                    "wlanvap": {"wl0": {}, "eth4": {}},
                }
            }
        },
    ),
    LiveboxSwitchEntityDescription(
        key="guest_wifi",
        name="Guest Wifi switch",
        icon=GUESTWIFI_ICON,
        translation_key="guest_wifi",
        value_fn=lambda x: getattr(getattr(x, "nemo"), "async_set_guest_wifi"),
        turn_on_parameters={"Enable": "true", "Status": "true"},
        turn_off_parameters={"Enable": "false", "Status": "false"},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LiveboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    switchs_description = SWITCH_TYPES_5 if coordinator.model == 5 else SWITCH_TYPES
    entities = [
        LiveboxSwitch(coordinator, description) for description in switchs_description
    ]

    for key, device in coordinator.data["devices"].items():
        entities.append(DeviceWANAccessSwitch(coordinator, key, device))

    async_add_entities(entities)


class LiveboxSwitch(LiveboxEntity, SwitchEntity):
    """Representation of a livebox switch."""

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        descrîption: SwitchEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, descrîption)

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self.coordinator.data.get(self.entity_description.key) is True

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self.entity_description.value_fn(self.coordinator.api)(
            self.entity_description.turn_on_parameters
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self.entity_description.value_fn(self.coordinator.api)(
            self.entity_description.turn_off_parameters
        )
        await self.coordinator.async_request_refresh()


class DeviceWANAccessSwitch(
    CoordinatorEntity[LiveboxDataUpdateCoordinator], SwitchEntity
):
    """Representation of a livebox device WAN access switch."""

    _attr_name = "WAN access"
    _attr_icon = DEVICE_WANACCESS_ICON
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        device_key: str,
        device: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_key = device_key
        self._device = device
        self._attr_name = "WAN access"
        self._attr_unique_id = f"{self._device_key}_wan_access"
        self._attr_device_info = {
            "name": self._device.get("Name"),
            "identifiers": {(DOMAIN, self._device_key)},
            "connections": {(dr.CONNECTION_NETWORK_MAC, self._device_key)},
            "via_device": (DOMAIN, coordinator.unique_id),
        }

    def _get_device_schedule(self) -> dict[str, Any]:
        """Get device schedule."""
        return self.coordinator.data.get("devices_wan_access", {}).get(
            self._device_key, False
        )

    @property
    def is_on(self) -> bool:
        """Return true if device currently have WAN access."""
        schedule = self._get_device_schedule()
        if (
            schedule
            and (schedule.get("override") == "Disable")
            and (schedule.get("value") == "Disable")
        ):
            return False
        return True

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        schedule = self._get_device_schedule()
        if schedule:
            parameters = {"type": "ToD", "ID": self._device_key, "override": "Enable"}
            result = await self.coordinator.api.schedule.async_set_schedule(parameters)
            if not isinstance(result, dict) or not result.get("status"):
                raise HomeAssistantError(
                    f"Fail to unlock device {self._device.get('Name')} ({self._device_key}) "
                    "WAN access"
                )
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        schedule = self._get_device_schedule()
        if schedule:
            parameters = {"type": "ToD", "ID": self._device_key, "override": "Disable"}
            result = await self.coordinator.api.schedule.async_set_schedule(parameters)
            if not isinstance(result, dict) or not result.get("status"):
                raise HomeAssistantError(
                    f"Fail to lock device {self._device.get('Name')} ({self._device_key}) "
                    "WAN access"
                )
            await self.coordinator.async_request_refresh()
        else:
            parameters = {
                "type": "ToD",
                "ID": self._device_key,
                "info": {
                    "base": "Weekly",
                    "def": "Enable",
                    "ID": self._device_key,
                    "schedule": [],
                    "enable": True,
                    "override": "Disable",
                },
            }
            result = await self.coordinator.api.schedule.async_add_schedule(parameters)
            if not isinstance(result, dict) or not result.get("status"):
                raise HomeAssistantError(
                    f"Fail to lock device {self._device.get('Name')} ({self._device_key}) "
                    "WAN access"
                )
            await self.coordinator.async_request_refresh()
