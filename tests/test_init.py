"""Tests for the Livebox integration setup helpers and services."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.livebox.const import DOMAIN


async def test_remove_call_missed_targets_loaded_entries(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """The service clears the call list of loaded entries only."""
    clear = AIOSysbus.voiceservice.async_clear_calllist = AsyncMock()
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "remove_call_missed",
        {"callId": "1", "config_entry_id": config_entry.entry_id},
        blocking=True,
    )
    clear.assert_awaited_once_with({"callId": "1"})

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "remove_call_missed", {"config_entry_id": "unknown"}, blocking=True
        )

    # The service outlives the entry and no longer reaches its coordinator.
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    clear.reset_mock()
    await hass.services.async_call(DOMAIN, "remove_call_missed", {}, blocking=True)
    clear.assert_not_awaited()
