"""Session persistence and logout for Livebox integration."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientSession, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from yarl import URL

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
    cookies: dict[str, str],
    *,
    verify_tls: bool = True,
) -> bool:
    """Logout from the Livebox by calling /logout.cmd with the session cookie."""
    try:
        url = URL(base_url).parent / "logout.cmd"
        headers = {
            "Cookie": ";".join(f"{key}={value}" for key, value in cookies.items())
        }
        async with http_session.get(
            str(url),
            headers=headers,
            allow_redirects=False,
            timeout=ClientTimeout(total=10),
            ssl=verify_tls,
        ) as response:
            if response.status in (200, 301, 302, 307):
                _LOGGER.debug(
                    "Successfully logged out from Livebox (status %s)",
                    response.status,
                )
                return True
            _LOGGER.debug("Logout returned unexpected status %s", response.status)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Logout failed: %s", err)
    return False
