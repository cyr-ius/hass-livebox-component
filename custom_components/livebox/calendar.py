"""Call log calendar for Livebox SIP gateway."""

import datetime
import logging
from typing import Any

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEntityDescription,
    CalendarEvent,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import LiveboxConfigEntry
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity

PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LiveboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the call log calendar."""

    coordinator = config_entry.runtime_data
    async_add_entities([LiveboxCallLogCalendar(coordinator)])


class LiveboxCallLogCalendarEntityDescription(CalendarEntityDescription):
    """A class that describes livebox call-log calendar entities."""

    initial_color: str = "#ff6600"


class LiveboxCallLogCalendar(LiveboxEntity, CalendarEntity):
    """A homeassistant calendar entity that represents the calls in the call log."""

    def __init__(self, coordinator: LiveboxDataUpdateCoordinator) -> None:
        """Initialize calendar."""

        entity_description = LiveboxCallLogCalendarEntityDescription(
            key="call_log_calendar",
            translation_key="call_log",
        )

        super().__init__(coordinator, entity_description)

        self._previous_uptime = 0
        self._calls: dict[int, CalendarEvent] = {}
        self._max_call_id = 0

    @property
    def event(self) -> CalendarEvent | None:
        """Returns None since there will never be a 'next event'."""
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calls within a datetime range."""
        assert start_date < end_date

        infos: dict[str, Any] = self.coordinator.data.get("infos") or {}
        current_uptime: int = infos.get("UpTime") or 0
        if current_uptime < self._previous_uptime:
            # Router has reset
            self._calls = {}
            self._max_call_id = 0
            _LOGGER.warning("Livebox has reset, clearing up call log")
        self._previous_uptime = current_uptime

        max_call_id_in_batch = 0
        for call in self.coordinator.data["callers"]:
            try:
                call_id = int(call["id"])
            except TypeError, ValueError:
                continue
            max_call_id_in_batch = max(max_call_id_in_batch, call_id)

            if call_id > self._max_call_id:
                try:
                    duration = int(call["duration"] or 0)
                except TypeError, ValueError:
                    duration = 0
                if (call_time := dt_util.parse_datetime(call["date"])) is None:
                    continue
                call_type = "Call" if call["status"] == "succeeded" else "Missed "
                call_direction = "to" if call["origin"] == "local" else "from"

                self._calls[call_id] = CalendarEvent(
                    start=call_time,
                    end=call_time + datetime.timedelta(seconds=duration),
                    summary="{} {} {}".format(
                        call_type,
                        call_direction,
                        call["phone_number"],
                    ),
                )

        self._max_call_id = max(max_call_id_in_batch, self._max_call_id)

        return [
            event
            for event in self._calls.values()
            if event.start < end_date and event.end > start_date
        ]
