"""Sensor for Livebox router."""
from dataclasses import dataclass
import logging
from typing import Any, Final

from aiosysbus import AiosysbusException

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_WANACCESS_ICON, DOMAIN, GUESTWIFI_ICON
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiveboxSwitchEntityDescription(SwitchEntityDescription):
    """Class describing Livebox button entities."""

    sub_api: str | None = None
    value_fn: str | None = None
    tunr_on_parameters: dict[str, Any] | None = None
    tunr_off_parameters: dict[str, Any] | None = None


SWITCH_TYPES: Final[tuple[SwitchEntityDescription, ...]] = (
    LiveboxSwitchEntityDescription(
        key="wifi",
        name="Wifi switch",
        translation_key="wifi_switch",
        sub_api="wifi",
        value_fn="async_set_wifi",
        tunr_on_parameters={"Enable": "true", "Status": "true"},
        tunr_off_parameters={"Enable": "false", "Status": "false"},
    ),
    LiveboxSwitchEntityDescription(
        key="guest_wifi",
        name="Guest Wifi switch",
        icon=GUESTWIFI_ICON,
        translation_key="guest_wifi",
        sub_api="guestwifi",
        value_fn="async_set_guest_wifi",
        tunr_on_parameters={"Enable": "true", "Status": "true"},
        tunr_off_parameters={"Enable": "false", "Status": "false"},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [LiveboxSwitch(coordinator, description) for description in SWITCH_TYPES]

    for key, device in coordinator.data["devices"].items():
        entities.append(DeviceWANAccessSwitch(coordinator, key, device))

    async_add_entities(entities, True)


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
        api = self.coordinator.api
        if sub_api := self.entity_description.sub_api:
            api = getattr(api, sub_api)
        try:
            await getattr(api, self.entity_description.value_fn)(
                self.entity_description.tunr_on_parameters
            )
        except AiosysbusException as error:
            _LOGGER.error(error)
        else:
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch on."""
        api = self.coordinator.api
        if sub_api := self.entity_description.sub_api:
            api = getattr(api, sub_api)
        try:
            await getattr(api, self.entity_description.value_fn)(
                self.entity_description.tunr_off_parameters
            )
        except AiosysbusException as error:
            _LOGGER.error(error)
        else:
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
            try:
                parameters = {
                    "type": "ToD",
                    "ID": self._device_key,
                    "override": "Enable",
                }
                result = await self.coordinator.api.schedule.async_set_schedule(
                    parameters
                )
                if not isinstance(result, dict) or not result.get("status"):
                    raise HomeAssistantError(
                        f"Fail to unlock device {self._device.get('Name')} ({self._device_key}) "
                        "WAN access"
                    )
            except AiosysbusException as error:
                _LOGGER.error(error)
            else:
                await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        schedule = self._get_device_schedule()
        if schedule:
            try:
                parameters = {
                    "type": "ToD",
                    "ID": self._device_key,
                    "override": "Disable",
                }
                result = await self.coordinator.api.schedule.async_set_schedule(
                    parameters
                )
                if not isinstance(result, dict) or not result.get("status"):
                    raise HomeAssistantError(
                        f"Fail to lock device {self._device.get('Name')} ({self._device_key}) "
                        "WAN access"
                    )
            except AiosysbusException as error:
                _LOGGER.error(error)
            else:
                await self.coordinator.async_request_refresh()
        else:
            try:
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
                result = await self.coordinator.api.schedule.async_add_schedule(
                    parameters
                )
                if not isinstance(result, dict) or not result.get("status"):
                    raise HomeAssistantError(
                        f"Fail to lock device {self._device.get('Name')} ({self._device_key}) "
                        "WAN access"
                    )

            except AiosysbusException as error:
                _LOGGER.error(error)
            else:
                await self.coordinator.async_request_refresh()
