"""Tests for the Livebox call log calendar."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_calendar_returns_overlapping_calls(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Calls overlapping the window are returned, calls without id are skipped."""
    call = {
        "remoteNumber": "0102030405",
        "startTime": "2026-10-10T10:00:00Z",
        "duration": 600,
        "callType": "succeeded",
        "callOrigin": "local",
    }
    AIOSysbus.api_raw["VoiceService.async_get_calllist"]["status"][:] = [
        {**call, "callId": "1"},
        {**call, "callId": None, "remoteNumber": "0607080910"},
    ]

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    (entity_id,) = hass.states.async_entity_ids("calendar")
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "start_date_time": "2026-10-10T10:05:00+00:00",
            "end_date_time": "2026-10-10T11:00:00+00:00",
        },
        target={"entity_id": entity_id},
        blocking=True,
        return_response=True,
    )

    events = response[entity_id]["events"]
    assert [event["summary"] for event in events] == ["Call to 0102030405"]
