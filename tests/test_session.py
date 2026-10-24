"""Tests for Livebox session management (logout + persistence)."""

from __future__ import annotations

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

# ---------------------------------------------------------------------------
# G1 — Unit: async_logout_session
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal async context manager mimicking aiohttp response."""

    def __init__(
        self,
        status: int,
        payload: object | None = None,
        json_error: Exception | None = None,
    ) -> None:
        self.status = status
        self.payload = payload
        self.json_error = json_error
        self.json_content_type: str | None = "not called"

    async def __aenter__(self) -> _FakeResponse:
        return self

    async def __aexit__(self, *args):
        pass

    async def json(self, content_type: str | None = None) -> object | None:
        self.json_content_type = content_type
        if self.json_error is not None:
            raise self.json_error
        return self.payload


def _set_mock_session(AIOSysbus: AsyncMock | MagicMock) -> None:
    """Set session credentials on the mocked router client."""
    AIOSysbus._auth.session_token = "session-context"
    AIOSysbus._auth._cookies = {"SESSIONID": "session-cookie"}
    AIOSysbus._auth.base_url = "http://192.168.1.1/ws"
    AIOSysbus._auth.verify_tls = False


@pytest.mark.parametrize("verify_tls", [True, False])
async def test_logout_session_success(verify_tls: bool) -> None:
    """Logout releases the context using the web UI request."""
    mock_session = MagicMock(spec=ClientSession)
    response = _FakeResponse(200, {"status": 0})
    mock_session.post = MagicMock(return_value=response)
    base_url = "http://192.168.1.1/ws"
    cookies = {"SESSIONID": "abc123", "token": "bbb"}

    result = await async_logout_session(
        mock_session,
        base_url,
        "ctx-123",
        cookies,
        verify_tls=verify_tls,
    )
    assert result is True

    call_args = mock_session.post.call_args
    assert call_args.args == (base_url,)
    assert call_args.kwargs["headers"] == {
        "Authorization": "X-Sah-Logout ctx-123",
        "Content-Type": "application/x-sah-ws-1-call+json",
        "Cookie": "SESSIONID=abc123;token=bbb",
    }
    assert call_args.kwargs["json"] == {
        "service": "sah.Device.Information",
        "method": "releaseContext",
        "parameters": {"applicationName": "so_sdkut"},
    }
    assert call_args.kwargs["ssl"] is verify_tls
    assert call_args.kwargs["timeout"].total == 10
    assert response.json_content_type is None


async def test_logout_session_failure_payload() -> None:
    """A successful HTTP response with errors does not release the session."""
    mock_session = MagicMock(spec=ClientSession)
    mock_session.post = MagicMock(
        return_value=_FakeResponse(
            200,
            {"result": {"errors": [{"error": 196618}]}},
        )
    )

    result = await async_logout_session(
        mock_session,
        "http://192.168.1.1/ws",
        "ctx-123",
        {"sessid": "abc123"},
    )
    assert result is False


async def test_logout_session_failure_status() -> None:
    """Logout returns False for non-success status codes."""
    mock_session = MagicMock(spec=ClientSession)
    mock_session.post = MagicMock(return_value=_FakeResponse(500, {"status": 0}))

    result = await async_logout_session(
        mock_session,
        "http://192.168.1.1/ws",
        "ctx-123",
        {"sessid": "abc123"},
    )
    assert result is False


async def test_logout_session_exception() -> None:
    """Logout returns False when the request raises an exception."""
    mock_session = MagicMock(spec=ClientSession)
    mock_session.post = MagicMock(side_effect=OSError("Connection refused"))

    result = await async_logout_session(
        mock_session,
        "http://192.168.1.1/ws",
        "ctx-123",
        {"sessid": "abc123"},
    )
    assert result is False


async def test_logout_session_non_json() -> None:
    """Logout returns False when the response body is not valid JSON."""
    mock_session = MagicMock(spec=ClientSession)
    mock_session.post = MagicMock(
        return_value=_FakeResponse(200, json_error=ValueError("Invalid JSON"))
    )

    result = await async_logout_session(
        mock_session,
        "http://192.168.1.1/ws",
        "ctx-123",
        {"sessid": "abc123"},
    )
    assert result is False


@pytest.mark.parametrize("context_id", [None, ""])
async def test_logout_session_missing_context_id(context_id: str | None) -> None:
    """Logout does not make a request without a context ID."""
    mock_session = MagicMock(spec=ClientSession)

    result = await async_logout_session(
        mock_session,
        "http://192.168.1.1/ws",
        context_id,
        {"sessid": "abc123"},
    )
    assert result is False
    mock_session.post.assert_not_called()


# ---------------------------------------------------------------------------
# G2 — Unit: LiveboxSessionStore round-trip
# ---------------------------------------------------------------------------


async def test_store_save_load_roundtrip(hass) -> None:
    """Save → load round-trip preserves all fields."""
    store = LiveboxSessionStore(hass, "test_entry_123")

    await store.async_save(
        cookies={"sessid": "cookie_val"},
        context_id="ctx_abc",
        base_url="http://192.168.1.1/ws",
        verify_tls=False,
    )

    # Create a fresh store instance (simulates restart)
    store2 = LiveboxSessionStore(hass, "test_entry_123")
    await store2.async_load()

    assert store2.has_session is True
    assert store2.cookies == {"sessid": "cookie_val"}
    assert store2.context_id == "ctx_abc"
    assert store2.base_url == "http://192.168.1.1/ws"
    assert store2.verify_tls is False


async def test_store_clear(hass) -> None:
    """async_clear empties the store."""
    store = LiveboxSessionStore(hass, "test_entry_clear")
    await store.async_save(
        cookies={"sessid": "x"},
        context_id="ctx",
        base_url="http://x/ws",
    )
    assert store.has_session is True

    await store.async_clear()
    assert store.has_session is False
    assert store.cookies == {}
    assert store.context_id is None


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
@pytest.mark.parametrize("logout_fails", [False, True])
async def test_unload_calls_api_logout_and_clears_persisted_session(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
    logout_fails: bool,
) -> None:
    """Unloading logs out through aiosysbus and clears persisted session data."""
    _set_mock_session(AIOSysbus)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    store = LiveboxSessionStore(hass, config_entry.entry_id)
    await store.async_load()
    assert store.has_session is True

    if logout_fails:
        AIOSysbus.async_logout.side_effect = HttpRequestFailed("Connection failed")

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    AIOSysbus.async_logout.assert_awaited_once()

    cleared_store = LiveboxSessionStore(hass, config_entry.entry_id)
    await cleared_store.async_load()
    assert cleared_store.has_session is False


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_orphan_cleanup_on_boot(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Setup releases an orphaned session and clears its persisted data."""
    store = LiveboxSessionStore(hass, config_entry.entry_id)
    await store.async_save(
        cookies={"sessid": "orphan_cookie"},
        context_id="orphan_ctx",
        base_url="http://192.168.1.1/ws",
        verify_tls=True,
    )

    with patch(
        "custom_components.livebox.session.async_logout_session",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_logout:
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    mock_logout.assert_awaited_once()
    call_kwargs = mock_logout.call_args
    assert call_kwargs[0][1] == "http://192.168.1.1/ws"
    assert call_kwargs[0][2] == "orphan_ctx"
    assert call_kwargs[0][3] == {"sessid": "orphan_cookie"}
    assert call_kwargs[1]["verify_tls"] is True

    await store.async_load()
    assert store.has_session is False
