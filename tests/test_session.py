"""Tests for the Livebox session saved to release it after a crash."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiosysbus.exceptions import HttpRequestFailed
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.livebox.const import DOMAIN

SESSION = {"context_id": "ctx-1", "cookies": {"AA/sessid": "cookie-1"}}
ORPHAN = {"context_id": "ctx-orphan", "cookies": {"AA/sessid": "cookie-orphan"}}


def _store_key(config_entry: ConfigEntry) -> str:
    """Return the storage key of the saved session."""
    return f"{DOMAIN}_session.{config_entry.entry_id}"


def _saved_session(
    hass_storage: dict[str, Any], config_entry: ConfigEntry
) -> dict[str, Any] | None:
    """Return the session saved in the storage, None when there is none."""
    stored = hass_storage.get(_store_key(config_entry))
    return stored["data"] if stored else None


async def _async_setup(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Set up the integration."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_orphaned_session_released_at_setup(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """A session left by a crash is released before the first update."""
    hass_storage[_store_key(config_entry)] = {
        "version": 1,
        "key": _store_key(config_entry),
        "data": ORPHAN,
    }

    await _async_setup(hass, config_entry)

    AIOSysbus.async_release_session.assert_awaited_once_with(ORPHAN)
    assert config_entry.state is ConfigEntryState.LOADED
    assert _saved_session(hass_storage, config_entry) is None


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_orphaned_session_release_failure_does_not_block_setup(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """An unreachable Livebox only skips the release, it is not retried."""
    hass_storage[_store_key(config_entry)] = {
        "version": 1,
        "key": _store_key(config_entry),
        "data": ORPHAN,
    }
    AIOSysbus.async_release_session.side_effect = HttpRequestFailed("unreachable")

    await _async_setup(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    assert _saved_session(hass_storage, config_entry) is None


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_no_release_without_saved_session(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Nothing is released after a clean stop."""
    await _async_setup(hass, config_entry)

    AIOSysbus.async_release_session.assert_not_awaited()


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_session_saved_when_it_changes(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """The open session is saved, and saved again only when it changes."""
    AIOSysbus.session_state = SESSION
    await _async_setup(hass, config_entry)
    assert _saved_session(hass_storage, config_entry) == SESSION

    # Unchanged session: the storage is not written again.
    hass_storage[_store_key(config_entry)]["data"] = {"marker": True}
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    assert _saved_session(hass_storage, config_entry) == {"marker": True}

    # New session after a re-authentication.
    renewed = {"context_id": "ctx-2", "cookies": {"AA/sessid": "cookie-2"}}
    AIOSysbus.session_state = renewed
    await coordinator.async_refresh()
    assert _saved_session(hass_storage, config_entry) == renewed

    # Session dropped: nothing left to release.
    AIOSysbus.session_state = None
    await coordinator.async_refresh()
    assert _saved_session(hass_storage, config_entry) is None


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
@pytest.mark.parametrize("logout_fails", [False, True])
async def test_unload_clears_saved_session(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
    logout_fails: bool,
) -> None:
    """A clean unload releases the session and forgets it."""
    AIOSysbus.session_state = SESSION
    await _async_setup(hass, config_entry)
    assert _saved_session(hass_storage, config_entry) == SESSION

    if logout_fails:
        AIOSysbus.async_logout.side_effect = HttpRequestFailed("unreachable")
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    AIOSysbus.async_logout.assert_awaited_once()
    assert _saved_session(hass_storage, config_entry) is None
