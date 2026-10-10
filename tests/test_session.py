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

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

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
    """Logout releases the session using the web UI request."""
    http_session = MagicMock(spec=ClientSession)
    response = _FakeResponse(200, {"status": 0})
    http_session.post.return_value = response
    base_url = "http://192.168.1.1/ws"
    cookies = {"SESSIONID": "session-cookie", "token": "second-cookie"}

    result = await async_logout_session(
        http_session,
        base_url,
        "session-context",
        cookies,
        verify_tls=verify_tls,
    )

    assert result is True
    call_args = http_session.post.call_args
    assert call_args.args == (base_url,)
    assert call_args.kwargs["headers"] == {
        "Authorization": "X-Sah-Logout session-context",
        "Content-Type": "application/x-sah-ws-1-call+json",
        "Cookie": "SESSIONID=session-cookie;token=second-cookie",
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
    """A successful HTTP response with errors does not release the context."""
    http_session = MagicMock(spec=ClientSession)
    http_session.post.return_value = _FakeResponse(
        200,
        {"result": {"errors": [{"error": 196618}]}},
    )

    result = await async_logout_session(
        http_session,
        "http://192.168.1.1/ws",
        "session-context",
        {"SESSIONID": "session-cookie"},
    )
    assert result is False


async def test_logout_session_failure_status() -> None:
    """Logout fails for unexpected HTTP statuses."""
    http_session = MagicMock(spec=ClientSession)
    http_session.post.return_value = _FakeResponse(500, {"status": 0})

    result = await async_logout_session(
        http_session,
        "http://192.168.1.1/ws",
        "session-context",
        {"SESSIONID": "session-cookie"},
    )
    assert result is False


async def test_logout_session_exception() -> None:
    """Logout returns False when the HTTP request raises."""
    http_session = MagicMock(spec=ClientSession)
    http_session.post.side_effect = OSError("Connection refused")

    result = await async_logout_session(
        http_session,
        "http://192.168.1.1/ws",
        "session-context",
        {"SESSIONID": "session-cookie"},
    )
    assert result is False


async def test_logout_session_non_json() -> None:
    """Logout returns False when the response is not valid JSON."""
    http_session = MagicMock(spec=ClientSession)
    http_session.post.return_value = _FakeResponse(
        200,
        json_error=ValueError("Invalid JSON"),
    )

    result = await async_logout_session(
        http_session,
        "http://192.168.1.1/ws",
        "session-context",
        {"SESSIONID": "session-cookie"},
    )
    assert result is False


@pytest.mark.parametrize("context_id", [None, ""])
async def test_logout_session_missing_context_id(context_id: str | None) -> None:
    """Logout does not make a request without a context ID."""
    http_session = MagicMock(spec=ClientSession)

    result = await async_logout_session(
        http_session,
        "http://192.168.1.1/ws",
        context_id,
        {"SESSIONID": "session-cookie"},
    )
    assert result is False
    http_session.post.assert_not_called()


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


@pytest.mark.parametrize(
    ("session_token", "cookies", "should_logout"),
    [
        (None, {"SESSIONID": "session-cookie"}, False),
        ("session-context", {}, False),
        ("session-context", {"SESSIONID": "session-cookie"}, True),
    ],
)
@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_unload_logout_uses_credentials_only(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
    session_token: str | None,
    cookies: dict[str, str],
    should_logout: bool,
) -> None:
    """Logout requires both context and cookies and passes the context ID."""
    _set_mock_session(AIOSysbus)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    AIOSysbus._auth.session_token = session_token
    AIOSysbus._auth._cookies = cookies
    with patch(
        "custom_components.livebox.coordinator.async_logout_session",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_logout:
        assert await hass.config_entries.async_unload(config_entry.entry_id) is True
        await hass.async_block_till_done()

    if should_logout:
        mock_logout.assert_awaited_once()
        assert mock_logout.call_args.args[1:] == (
            "http://192.168.1.1/ws",
            "session-context",
            {"SESSIONID": "session-cookie"},
        )
        assert mock_logout.call_args.kwargs["verify_tls"] is False
    else:
        mock_logout.assert_not_awaited()

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
        "orphan-context",
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
