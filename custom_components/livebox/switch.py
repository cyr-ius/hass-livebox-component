"""Sensor for Livebox router."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LiveboxConfigEntry
from .const import DEVICE_WANACCESS_ICON, DOMAIN, GUESTWIFI_ICON
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiveboxSwitchEntityDescription(SwitchEntityDescription):
    """Class describing Livebox button entities."""

    value_fn: Callable[..., Any] | None = None
    turn_on: Callable[..., Any] | None = None
    turn_off: Callable[..., Any] | None = None


SWITCH_TYPES: Final[tuple[LiveboxSwitchEntityDescription, ...]] = (
    LiveboxSwitchEntityDescription(
        key="wifi",
        name="Wifi",
        translation_key="wifi_switch",
        value_fn=lambda x: x.get("wifi"),
        turn_on=lambda x: x.nmc.async_set_wifi({"Enable": True, "Status": True}),
        turn_off=lambda x: x.nmc.async_set_wifi({"Enable": False, "Status": False}),
    ),
    LiveboxSwitchEntityDescription(
        key="guest_wifi",
        name="Guest Wifi",
        icon=GUESTWIFI_ICON,
        translation_key="guest_wifi",
        value_fn=lambda x: x.get("guest_wifi"),
        turn_on=lambda x: x.nmc.async_set_guest_wifi(enable=True),
        turn_off=lambda x: x.nmc.async_set_guest_wifi(enable=False),
    ),
)

SWITCH_TYPES_5: Final[tuple[LiveboxSwitchEntityDescription, ...]] = (
    LiveboxSwitchEntityDescription(
        key="wifi",
        name="Wifi",
        translation_key="wifi_switch",
        value_fn=lambda x: x.get("wifi"),
        turn_on=lambda x: x.nemo.async_wifi(True),
        turn_off=lambda x: x.nemo.async_wifi(False),
    ),
    LiveboxSwitchEntityDescription(
        key="guest_wifi",
        name="Guest Wifi",
        icon=GUESTWIFI_ICON,
        translation_key="guest_wifi",
        value_fn=lambda x: x.get("guest_wifi"),
        turn_on=lambda x: x.nmc.async_guest_wifi(True),
        turn_off=lambda x: x.nmc.async_guest_wifi(False),
    ),
)

SWITCH_WAN_ACCESS: SwitchEntityDescription = SwitchEntityDescription(
    key="wan_access",
    name="WAN access",
    translation_key="wan_access",
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

    for device in coordinator.data["devices"].values():
        entities.append(DeviceWANAccessSwitch(coordinator, SWITCH_WAN_ACCESS, device))

    async_add_entities(entities)


class LiveboxSwitch(LiveboxEntity, SwitchEntity):
    """Representation of a livebox switch."""

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        descrîption: LiveboxSwitchEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, descrîption)

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self.entity_description.value_fn(self.coordinator.data) is True

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self.entity_description.turn_on(self.coordinator.api)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self.entity_description.turn_off(self.coordinator.api)
        await self.coordinator.async_request_refresh()


class DeviceWANAccessSwitch(LiveboxEntity, SwitchEntity):
    """Representation of a livebox device WAN access switch."""

    _attr_icon = DEVICE_WANACCESS_ICON

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        description: SwitchEntityDescription,
        device: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)
        self._device_key = device.get("Key")
        self._device = device
        self._attr_unique_id = f"{self._device_key}_{description.key}"
        self._attr_name = f"{self._device.get('Name')} {description.name}"
        self._attr_device_info = {
            "name": self._unique_name,
            "identifiers": {(DOMAIN, self._device_key)},
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
