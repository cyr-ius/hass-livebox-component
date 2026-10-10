"""Session persistence and logout for Livebox integration."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientSession, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "livebox_session"
STORAGE_VERSION = 1


class LiveboxSessionStore:
    """Persists Livebox session credentials for clean logout on restart."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the session store."""
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry_id}"
        )
        self._data: dict[str, Any] = {}

    async def async_load(self) -> None:
        """Load persisted session data."""
        data = await self._store.async_load()
        self._data = data or {}

    async def async_save(
        self,
        cookies: dict[str, str],
        context_id: str | None,
        base_url: str,
        *,
        verify_tls: bool = True,
    ) -> None:
        """Save current session credentials."""
        self._data = {
            "cookies": cookies,
            "context_id": context_id,
            "base_url": base_url,
            "verify_tls": verify_tls,
        }
        await self._store.async_save(self._data)

    async def async_clear(self) -> None:
        """Clear stored session data."""
        self._data = {}
        await self._store.async_save(self._data)

    @property
    def cookies(self) -> dict[str, str]:
        """Return stored cookies."""
        return self._data.get("cookies", {})

    @property
    def context_id(self) -> str | None:
        """Return stored context ID."""
        return self._data.get("context_id")

    @property
    def base_url(self) -> str | None:
        """Return stored base URL."""
        return self._data.get("base_url")

    @property
    def has_session(self) -> bool:
        """Return True if we have stored session credentials."""
        return bool(self._data.get("cookies"))

    @property
    def verify_tls(self) -> bool:
        """Return stored verify_tls setting (defaults to True)."""
        return self._data.get("verify_tls", True)


async def async_logout_session(
    http_session: ClientSession,
    base_url: str,
    context_id: str | None,
    cookies: dict[str, str],
    *,
    verify_tls: bool = True,
) -> bool:
    """Release the Livebox session using the web UI's releaseContext request.

    Returns True only when the Livebox confirms the context was released.
    """
    if not context_id:
        _LOGGER.debug("Skipped Livebox logout without a context ID")
        return False

    try:
        headers = {
            "Authorization": f"X-Sah-Logout {context_id}",
            "Content-Type": "application/x-sah-ws-1-call+json",
            "Cookie": ";".join(f"{key}={value}" for key, value in cookies.items()),
        }
        async with http_session.post(
            base_url,
            headers=headers,
            json={
                "service": "sah.Device.Information",
                "method": "releaseContext",
                "parameters": {"applicationName": "so_sdkut"},
            },
            timeout=ClientTimeout(total=10),
            ssl=verify_tls,
        ) as response:
            if response.status != 200:
                _LOGGER.debug("Logout returned unexpected status %s", response.status)
                return False

            response_data = await response.json(content_type=None)
            if isinstance(response_data, dict) and response_data.get("status") == 0:
                _LOGGER.debug("Successfully released Livebox session context")
                return True

            _LOGGER.debug("Livebox logout response did not confirm context release")
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Logout failed: %s", err)
    return False
