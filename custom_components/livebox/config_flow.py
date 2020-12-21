"""Config flow to configure Livebox."""
import logging

import voluptuous as vol
from aiosysbus.exceptions import (
    AuthorizationError,
    InsufficientPermissionsError,
    NotOpenError,
)
from homeassistant import config_entries, core
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .bridge import BridgeData, LiveboxException
from .const import (
    CONF_LAN_TRACKING,
    CONF_TRACKING_TIMEOUT,
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
    }
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    bridge = BridgeData(hass=hass, config_flow_data=data)
    await bridge.async_connect()

    return await bridge.async_get_infos()


class LiveboxFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Livebox config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the Livebox flow."""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get option flow."""
        return LiveboxOptionsFlowHandler(config_entry)

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            try:
                infos = await validate_input(self.hass, user_input)
                await self.async_set_unique_id(infos["SerialNumber"])
                self._abort_if_unique_id_configured()
            except AuthorizationError:
                errors["base"] = "login_inccorect"
            except InsufficientPermissionsError:
                errors["base"] = "insufficient_permission"
            except NotOpenError:
                errors["base"] = "cannot_connect"
            except LiveboxException:
                errors["base"] = "unknown"

            if "base" not in errors:
                return self.async_create_entry(
                    title=infos["ProductClass"], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class LiveboxOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle option."""

    def __init__(self, config_entry):
        """Initialize the options flow."""
        self.config_entry = config_entry
        self._lan_tracking = self.config_entry.options.get(
            CONF_LAN_TRACKING, DEFAULT_LAN_TRACKING
        )
        self._tracking_timeout = self.config_entry.options.get(
            CONF_TRACKING_TIMEOUT, DEFAULT_TRACKING_TIMEOUT
        )

    async def async_step_init(self, user_input=None):
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
