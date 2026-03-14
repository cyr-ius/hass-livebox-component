"""Call log calendar for Livebox SIP gateway."""

from __future__ import annotations

import datetime
from dateutil import parser
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LiveboxConfigEntry
from .entity import LiveboxEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LiveboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the call log calendar."""

    coordinator = config_entry.runtime_data
    async_add_entities([LiveboxCallLogCalendar(coordinator)])


class LiveboxCallLogCalendar(LiveboxEntity, CalendarEntity):
    """A homeassistant calendar entity that represents the calls in the call log."""

    def __init__(self, coordinator: LiveboxDataUpdateCoordinator) -> None:
        """Initialize calendar."""

        entity_description = EntityDescription(
            key="call_log_calendar",
            name="Call Log"
        )

        super().__init__(coordinator, entity_description)

        self._previous_uptime = 0
        self._calls = {}
        self._max_call_id = 0

    @property
    def event(self) -> CalendarEvent:
        """Returns None since there will never be a 'next event'."""
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Parses the coordinator's call log and returns calls within a datetime range."""
        assert start_date < end_date

        current_uptime = self.coordinator.data.get("infos").get("UpTime") or 0
        if current_uptime < self._previous_uptime:
            # Router has reset
            self._calls = {}
            self._max_call_id = 0
            _LOGGER.warning("Livebox has reset, clearing up call log")
        self._previous_uptime = current_uptime

        max_call_id_in_batch = 0
        for call in self.coordinator.data['callers']:
            call_id = int(call['id'])
            max_call_id_in_batch = max(max_call_id_in_batch, call_id)

            if call_id > self._max_call_id:
                call_time = parser.parse(call['date'])
                call_type = "Call" if call['status']=="succeeded" else "Missed "
                call_direction = "to" if call['origin']=="local" else "from"

                self._calls[call_id] = CalendarEvent(
                    start=call_time,
                    end=call_time + + datetime.timedelta(seconds=call['duration']),
                    summary='{0} {1} {2}'.format(call_type, call_direction, call['phone_number'])
                )

        self._max_call_id = max(max_call_id_in_batch, self._max_call_id)

        return filter(lambda ev: ev.start > start_date and ev.end < end_date, self._calls.values())

