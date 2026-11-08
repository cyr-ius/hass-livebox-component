"""Button for Livebox router."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.components.button.const import ButtonDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LiveboxConfigEntry
from .entity import LiveboxEntity
from .helpers import async_call_api

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class LiveboxButtonEntityDescription(ButtonEntityDescription):
    """Class describing Livebox button entities."""

    value_fn: Callable[..., Any]


BUTTON_TYPES: Final[tuple[LiveboxButtonEntityDescription, ...]] = (
    LiveboxButtonEntityDescription(
        key="restart",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        translation_key="restart_btn",
        value_fn=lambda x: x.nmc.async_reboot,
    ),
    LiveboxButtonEntityDescription(
        key="ring",
        translation_key="ring_btn",
        value_fn=lambda x: x.voiceservice.async_ring,
    ),
    LiveboxButtonEntityDescription(
        key="clear_calls",
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

    entity_description: LiveboxButtonEntityDescription
    _attr_should_poll = False

    async def async_press(self) -> None:
        """Triggers the button press service."""
        await async_call_api(self.entity_description.value_fn(self.coordinator.api)())
