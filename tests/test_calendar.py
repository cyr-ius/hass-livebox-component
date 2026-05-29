"""Minimal tests for the Livebox call-log calendar entity."""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.components.calendar import CalendarEvent

from custom_components.livebox.calendar import LiveboxCallLogCalendar
from custom_components.livebox.coordinator import LiveboxDataUpdateCoordinator


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations() -> None:
    """Avoid pulling the Home Assistant test harness into pure unit tests."""


def _make_coordinator(callers: list[dict[str, Any]]) -> LiveboxDataUpdateCoordinator:
    """Return a minimal coordinator stub with the given callers."""
    coordinator = object.__new__(LiveboxDataUpdateCoordinator)
    coordinator.data = {
        "callers": callers,
        "infos": {"UpTime": 12345},
    }
    return coordinator


def _make_calendar(callers: list[dict[str, Any]]) -> LiveboxCallLogCalendar:
    """Build a LiveboxCallLogCalendar backed by a stub coordinator."""
    coordinator = _make_coordinator(callers)
    calendar = object.__new__(LiveboxCallLogCalendar)
    calendar.coordinator = coordinator
    calendar._previous_uptime = 0
    calendar._calls = {}
    calendar._max_call_id = 0

    # Satisfy LiveboxEntity.__init__ without an actual hass instance
    calendar.hass = MagicMock()
    return calendar


_CALLERS = [
    {
        "id": "1",
        "date": "2024-06-01 10:00:00+00:00",
        "status": "succeeded",
        "origin": "remote",
        "phone_number": "+33600000001",
        "duration": 60,
    },
    {
        "id": "2",
        "date": "2024-06-01 11:00:00+00:00",
        "status": "missed",
        "origin": "remote",
        "phone_number": "+33600000002",
        "duration": 0,
    },
]


async def test_async_get_events_returns_list() -> None:
    """async_get_events must return a list (not a lazy iterator)."""
    calendar = _make_calendar(_CALLERS)

    start = datetime.datetime(2024, 6, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end = datetime.datetime(2024, 6, 2, 0, 0, 0, tzinfo=datetime.timezone.utc)

    result = await calendar.async_get_events(MagicMock(), start, end)

    assert isinstance(result, list), "async_get_events must return a list"
    assert len(result) > 0, "Expected at least one event in range"
    assert all(isinstance(ev, CalendarEvent) for ev in result)


async def test_async_get_events_filters_by_range() -> None:
    """Events outside the requested window must not be returned."""
    calendar = _make_calendar(_CALLERS)

    # Window that only covers the first call (10:00–11:00)
    start = datetime.datetime(2024, 6, 1, 9, 0, 0, tzinfo=datetime.timezone.utc)
    end = datetime.datetime(2024, 6, 1, 10, 30, 0, tzinfo=datetime.timezone.utc)

    result = await calendar.async_get_events(MagicMock(), start, end)

    assert isinstance(result, list)
    assert len(result) == 1
    assert "+33600000001" in result[0].summary
