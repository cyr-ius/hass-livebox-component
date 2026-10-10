"""Tests pour l'intégration Bbox2 utilisant config_entries."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiosysbus.exceptions import HttpRequestFailed
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Test du setup via une config entry."""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_coordinator_refresh(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Test du setup via une config entry."""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED

    coordinator = config_entry.runtime_data
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_unload_releases_session(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Unloading the entry releases the Livebox session."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    AIOSysbus.async_logout.assert_not_awaited()

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.NOT_LOADED
    AIOSysbus.async_logout.assert_awaited_once()


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_unload_logout_error(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """A failed logout does not prevent the entry from unloading."""
    AIOSysbus.async_logout.side_effect = HttpRequestFailed("Connection failed")
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_stop_releases_session(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Stopping Home Assistant releases the session of a loaded entry."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()

    AIOSysbus.async_logout.assert_awaited_once()


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_setup_retry_releases_session(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """A failed first refresh releases the session before the next attempt."""
    AIOSysbus.deviceinfo.async_get_deviceinfo.side_effect = HttpRequestFailed(
        "Connection failed"
    )

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.SETUP_RETRY
    AIOSysbus.async_logout.assert_awaited_once()
