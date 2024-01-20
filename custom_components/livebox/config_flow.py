"""Config flow to configure Livebox."""
from collections.abc import Mapping
import logging
from typing import Any
from urllib.parse import urlparse

from aiosysbus import AIOSysbus
from aiosysbus.exceptions import (
    AiosysbusException,
    AuthenticationFailed,
    InsufficientPermissionsError,
    NotOpenError,
)
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.components.ssdp import ATTR_SSDP_UDN, ATTR_SSDP_USN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_UNIQUE_ID,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import (
    CONF_LAN_TRACKING,
    CONF_TRACKING_TIMEOUT,
    CONF_USE_TLS,
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
        if user_input is not None and user_input.get(CONF_USERNAME) is not None:
            try:
                api = AIOSysbus(
                    username=user_input["username"],
                    password=user_input["password"],
                    session=async_create_clientsession(self.hass),
                    host=user_input["host"],
                    port=user_input["port"],
                )
                await api.async_connect()
                await api.async_get_permissions()
                infos = await api.deviceinfo.async_get_deviceinfo()
                if sn := infos.get("SerialNumber") is None:
                    raise NotOpenError("Serial number of device not found")
                await self.async_set_unique_id(sn)
                self._abort_if_unique_id_configured()
            except AuthenticationFailed:
                errors["base"] = "login_incorrect"
            except InsufficientPermissionsError:
                errors["base"] = "insufficient_permission"
            except NotOpenError:
                errors["base"] = "cannot_connect"
            except AiosysbusException:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=infos.get("ProductClass", DOMAIN), data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_ssdp(self, discovery_info: ssdp.SsdpServiceInfo) -> FlowResult:
        """Handle a discovered device."""
        hostname = urlparse(discovery_info.ssdp_location).hostname
        friendly_name = discovery_info.upnp[ssdp.ATTR_UPNP_FRIENDLY_NAME]
        unique_id = discovery_info.upnp[ssdp.ATTR_UPNP_SERIAL]
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        user_input = {
            CONF_HOST: hostname,
            CONF_NAME: friendly_name,
            CONF_UNIQUE_ID: unique_id,
            ATTR_SSDP_USN: discovery_info.ssdp_usn,
            ATTR_SSDP_UDN: discovery_info.ssdp_udn,
        }
        return await self.async_step_user(user_input)


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
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=options_schema)
