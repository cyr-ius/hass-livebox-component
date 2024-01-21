"""Button for Livebox router."""
from dataclasses import dataclass
import logging
from typing import Final

from aiosysbus import AiosysbusException

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, RESTART_ICON, RING_ICON
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiveboxButtonEntityDescription(ButtonEntityDescription):
    """Class describing Livebox button entities."""

    sub_api: str | None = None
    value_fn: str | None = None


BUTTON_TYPES: Final[tuple[ButtonEntityDescription, ...]] = (
    LiveboxButtonEntityDescription(
        key="restart",
        name="Livebox restart",
        icon=RESTART_ICON,
        translation_key="restart_btn",
        sub_api="system",
        value_fn="async_reboot",
    ),
    LiveboxButtonEntityDescription(
        key="ring",
        name="Ring your phone",
        icon=RING_ICON,
        translation_key="ring_btn",
        sub_api="call",
        value_fn="async_set_voiceapplication_ring",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [Button(coordinator, description) for description in BUTTON_TYPES]
    async_add_entities(entities)


class Button(LiveboxEntity, ButtonEntity):
    """Representation of a livebox button."""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        entity_description: LiveboxButtonEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entity_description)

    async def async_press(self) -> None:
        """Triggers the button press service."""
        api = self.coordinator.api
        if sub_api := self.entity_description.sub_api:
            api = getattr(api, sub_api)

        try:
            await getattr(api, self.entity_description.value_fn)()
        except AiosysbusException as error:
            _LOGGER.error(error)
