"""Tests for Livebox session persistence and logout."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession
from aiosysbus.exceptions import HttpRequestFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.livebox.session import (
    LiveboxSessionStore,
    async_logout_session,
)


class _FakeResponse:
    """Minimal async context manager mimicking an aiohttp response."""

    def __init__(self, status: int) -> None:
        self.status = status

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


def _set_mock_session(AIOSysbus: AsyncMock | MagicMock) -> None:
    """Set session credentials on the mocked router client."""
    AIOSysbus._auth.session_token = "session-context"
    AIOSysbus._auth._cookies = {"SESSIONID": "session-cookie"}
    AIOSysbus._auth.base_url = "http://192.168.1.1/ws"
    AIOSysbus._auth.verify_tls = False


@pytest.mark.parametrize("status", [200, 301, 302, 307])
async def test_logout_session_success_statuses(status: int) -> None:
    """Logout succeeds for successful responses and redirects."""
    http_session = MagicMock(spec=ClientSession)
    http_session.get.return_value = _FakeResponse(status)

    result = await async_logout_session(
        http_session,
        "http://192.168.1.1/ws",
        {"SESSIONID": "session-cookie"},
    )

    assert result is True
    http_session.get.assert_called_once()
    assert http_session.get.call_args.args[0] == "http://192.168.1.1/logout.cmd"
    assert http_session.get.call_args.kwargs["headers"]["Cookie"] == (
        "SESSIONID=session-cookie"
    )


async def test_logout_session_verify_tls_false() -> None:
    """Logout passes the configured TLS verification setting to aiohttp."""
    http_session = MagicMock(spec=ClientSession)
    http_session.get.return_value = _FakeResponse(307)

    result = await async_logout_session(
        http_session,
        "https://192.168.1.1/ws",
        {"SESSIONID": "session-cookie"},
        verify_tls=False,
    )

    assert result is True
    assert http_session.get.call_args.kwargs["ssl"] is False


async def test_logout_session_failure_status() -> None:
    """Logout fails for unexpected HTTP statuses."""
    http_session = MagicMock(spec=ClientSession)
    http_session.get.return_value = _FakeResponse(404)

    assert (
        await async_logout_session(
            http_session,
            "http://192.168.1.1/ws",
            {"SESSIONID": "session-cookie"},
        )
        is False
    )


async def test_logout_session_exception() -> None:
    """Logout returns False when the HTTP request raises."""
    http_session = MagicMock(spec=ClientSession)
    http_session.get.side_effect = OSError("Connection refused")

    assert (
        await async_logout_session(
            http_session,
            "http://192.168.1.1/ws",
            {"SESSIONID": "session-cookie"},
        )
        is False
    )


async def test_logout_session_multiple_cookies() -> None:
    """Logout joins all session cookies in its request header."""
    http_session = MagicMock(spec=ClientSession)
    http_session.get.return_value = _FakeResponse(307)

    await async_logout_session(
        http_session,
        "http://192.168.1.1/ws",
        {"SESSIONID": "first", "token": "second"},
    )

    cookie_header = http_session.get.call_args.kwargs["headers"]["Cookie"]
    assert "SESSIONID=first" in cookie_header
    assert "token=second" in cookie_header


async def test_store_save_load_roundtrip(hass: HomeAssistant) -> None:
    """The store persists all values required for a later logout."""
    store = LiveboxSessionStore(hass, "session-roundtrip")
    await store.async_save(
        cookies={"SESSIONID": "session-cookie"},
        context_id="session-context",
        base_url="http://192.168.1.1/ws",
        verify_tls=False,
    )

    loaded_store = LiveboxSessionStore(hass, "session-roundtrip")
    await loaded_store.async_load()

    assert loaded_store.has_session is True
    assert loaded_store.cookies == {"SESSIONID": "session-cookie"}
    assert loaded_store.context_id == "session-context"
    assert loaded_store.base_url == "http://192.168.1.1/ws"
    assert loaded_store.verify_tls is False


async def test_store_clear(hass: HomeAssistant) -> None:
    """Clearing the store removes persisted session credentials."""
    store = LiveboxSessionStore(hass, "session-clear")
    await store.async_save(
        cookies={"SESSIONID": "session-cookie"},
        context_id="session-context",
        base_url="http://192.168.1.1/ws",
    )
    await store.async_clear()

    loaded_store = LiveboxSessionStore(hass, "session-clear")
    await loaded_store.async_load()
    assert loaded_store.has_session is False


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_coordinator_persists_session(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """A successful coordinator update persists credentials for restart logout."""
    _set_mock_session(AIOSysbus)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    store = LiveboxSessionStore(hass, config_entry.entry_id)
    await store.async_load()
    assert store.has_session is True
    assert store.cookies == {"SESSIONID": "session-cookie"}
    assert store.context_id == "session-context"
    assert store.verify_tls is False


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_coordinator_persists_only_changed_session(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Repeated updates save stable credentials once and save changed ones again."""
    _set_mock_session(AIOSysbus)

    with patch.object(
        LiveboxSessionStore, "async_save", new_callable=AsyncMock
    ) as mock_save:
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        coordinator = config_entry.runtime_data
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        mock_save.assert_awaited_once()

        AIOSysbus._auth.session_token = "updated-session-context"
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        assert mock_save.await_count == 2
        assert mock_save.await_args_list[-1].kwargs["context_id"] == (
            "updated-session-context"
        )


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_unload_logs_out_persisted_session(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Unloading the real config entry logs out its active router session."""
    _set_mock_session(AIOSysbus)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.livebox.coordinator.async_logout_session",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_logout:
        assert await hass.config_entries.async_unload(config_entry.entry_id) is True
        await hass.async_block_till_done()

    mock_logout.assert_awaited_once()
    assert mock_logout.call_args.args[1:] == (
        "http://192.168.1.1/ws",
        {"SESSIONID": "session-cookie"},
    )
    assert mock_logout.call_args.kwargs["verify_tls"] is False

    store = LiveboxSessionStore(hass, config_entry.entry_id)
    await store.async_load()
    assert store.has_session is False


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_setup_logs_out_orphaned_session(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Setup releases credentials saved by a previous Home Assistant run."""
    store = LiveboxSessionStore(hass, config_entry.entry_id)
    await store.async_save(
        cookies={"SESSIONID": "orphan-cookie"},
        context_id="orphan-context",
        base_url="http://192.168.1.1/ws",
        verify_tls=False,
    )

    with patch(
        "custom_components.livebox.session.async_logout_session",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_logout:
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    mock_logout.assert_awaited_once()
    assert mock_logout.call_args.args[1:] == (
        "http://192.168.1.1/ws",
        {"SESSIONID": "orphan-cookie"},
    )
    assert mock_logout.call_args.kwargs["verify_tls"] is False

    loaded_store = LiveboxSessionStore(hass, config_entry.entry_id)
    await loaded_store.async_load()
    assert loaded_store.has_session is False


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_http_request_failed_invalidates_session_token(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """A top-level communication failure clears the stale authentication token."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    AIOSysbus._auth.session_token = "stale-session-context"
    AIOSysbus.deviceinfo.async_get_deviceinfo.side_effect = HttpRequestFailed(
        "Connection failed"
    )
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert AIOSysbus._auth.session_token is None
