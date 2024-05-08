"""Config flow to configure Livebox."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from aiosysbus import AIOSysbus
from aiosysbus.exceptions import (
    AiosysbusException,
    AuthenticationFailed,
    HttpRequestFailed,
    InsufficientPermissionsError,
    RetrieveFailed,
)
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import (
    CONF_LAN_TRACKING,
    CONF_TRACKING_TIMEOUT,
    CONF_USE_TLS,
    CONF_VERIFY_TLS,
    DEFAULT_HOST,
    DEFAULT_LAN_TRACKING,
    DEFAULT_PORT,
    DEFAULT_TRACKING_TIMEOUT,
    DEFAULT_USERNAME,
    DOMAIN,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_USE_TLS, default=False): bool,
        vol.Required(CONF_VERIFY_TLS, default=True): bool,
    }
)

_LOGGER = logging.getLogger(__name__)


class LiveboxFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Livebox config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get option flow."""
        return LiveboxOptionsFlowHandler(config_entry)

    async def async_step_import(self, import_config) -> FlowResult:
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_user(
        self, user_input: Mapping[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input:
            try:
                api = AIOSysbus(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    session=async_create_clientsession(self.hass),
                    host=user_input[CONF_HOST],
                    port=user_input[CONF_PORT],
                    use_tls=user_input[CONF_USE_TLS],
                    verify_tls=user_input[CONF_VERIFY_TLS],
                )
                await api.async_connect()
                await api.async_get_permissions()

                infos = await api.deviceinfo.async_get_deviceinfo()
                if sn := infos.get("status", {}).get("SerialNumber") is None:
                    raise RetrieveFailed("Serial number of device not found")

                await self.async_set_unique_id(sn)
                self._abort_if_unique_id_configured()
            except AuthenticationFailed as err:
                _LOGGER.warning("Fail to authenticate to the Livebox: %s", err)
                errors["base"] = "login_incorrect"
            except InsufficientPermissionsError as err:
                _LOGGER.warning(
                    "Insufficient permissions error occurred connecting to the Livebox: %s",
                    err,
                )
                errors["base"] = "insufficient_permission"
            except (RetrieveFailed, HttpRequestFailed) as err:
                _LOGGER.warning("Fail to connect to the Livebox: %s", err)
                errors["base"] = "cannot_connect"
            except AiosysbusException as err:
                _LOGGER.exception("Unknown error connecting to the Livebox: %s", err)
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=infos.get("ProductClass", DOMAIN.capitalize()),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_ssdp(self, discovery_info: ssdp.SsdpServiceInfo) -> FlowResult:
        """Handle a discovered device."""
        unique_id = discovery_info.upnp[ssdp.ATTR_UPNP_SERIAL]
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return await self.async_step_user()


class LiveboxOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle option."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize the options flow."""
        self.config_entry = config_entry
        self._lan_tracking = self.config_entry.options.get(
            CONF_LAN_TRACKING, DEFAULT_LAN_TRACKING
        )
        self._tracking_timeout = self.config_entry.options.get(
            CONF_TRACKING_TIMEOUT, DEFAULT_TRACKING_TIMEOUT
        )

    async def async_step_init(
        self, user_input: Mapping[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        options_schema = vol.Schema(
            {
                vol.Required(CONF_LAN_TRACKING, default=self._lan_tracking): bool,
                vol.Required(
                    CONF_TRACKING_TIMEOUT, default=self._tracking_timeout
                ): int,
            },
        )
        if user_input:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=options_schema)
