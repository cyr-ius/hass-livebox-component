"""Button for Livebox router."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LiveboxConfigEntry
from .const import CLEARCALLS_ICON, RESTART_ICON, RING_ICON
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity


@dataclass(frozen=True, kw_only=True)
class LiveboxButtonEntityDescription(ButtonEntityDescription):
    """Class describing Livebox button entities."""

    value_fn: Callable[..., Any]


BUTTON_TYPES: Final[tuple[ButtonEntityDescription, ...]] = (
    LiveboxButtonEntityDescription(
        key="restart",
        name="Livebox restart",
        icon=RESTART_ICON,
        translation_key="restart_btn",
        value_fn=lambda x: x.nmc.async_reboot,
    ),
    LiveboxButtonEntityDescription(
        key="ring",
        name="Ring your phone",
        icon=RING_ICON,
        translation_key="ring_btn",
        value_fn=lambda x: x.voiceservice.async_ring,
    ),
    LiveboxButtonEntityDescription(
        key="clear_calls",
        name="Clear calls",
        icon=CLEARCALLS_ICON,
        translation_key="cmissed_clear_btn",
        value_fn=lambda x: x.voiceservice.async_clear_calllist,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LiveboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    entities = [Button(coordinator, description) for description in BUTTON_TYPES]
    async_add_entities(entities)


class Button(LiveboxEntity, ButtonEntity):
    """Representation of a livebox button."""

    _attr_should_poll = False
    entity_description: LiveboxButtonEntityDescription

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        description: LiveboxButtonEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description)

    async def async_press(self) -> None:
        """Triggers the button press service."""
        await self.entity_description.value_fn(self.coordinator.api)()
