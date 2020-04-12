"""Config flow to configure Livebox."""
import logging

from aiosysbus import Sysbus
from aiosysbus.exceptions import AuthorizationError
import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback

from .const import (
    CONF_LAN_TRACKING,
    DEFAULT_HOST,
    DEFAULT_LAN_TRACKING,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    DOMAIN,
    TEMPLATE_SENSOR,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    try:
        session = Sysbus(
            username=data["username"],
            password=data["password"],
            host=data["host"],
            port=data["port"],
        )

        perms = await session.async_get_permissions()
        if perms is not None:
            return await session.system.get_deviceinfo()

    except AuthorizationError:
        raise AuthorizationError
    except Exception as e:
        _LOGGER.warn("Error to connect {}".format(e))
        raise AuthorizationError
    

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
                if infos is not None:
                    return await self.async_step_register(infos, user_input)
            except AuthorizationError:
                errors["base"] = "login_inccorect"
            except Exception:   # pylint: disable=broad-except
                errors["base"] = "linking"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_register(self, infos, user_input=None):
        """Step for register component."""
        errors = {}
        box_id = infos.get("status",{}).get("SerialNumber")
        title = infos.get("status",{}).get("ProductClass")
        title 
        if box_id is not None:
            await self.async_set_unique_id(box_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=title, data=user_input)
            
        errors["base"] = "register_failed"
        return self.async_show_form(step_id="register", errors=errors)


class LiveboxOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle option."""

    def __init__(self, config_entry):
        """Initialize the options flow."""

        self.config_entry = config_entry
        self._lan_tracking = self.config_entry.options.get(
            CONF_LAN_TRACKING, DEFAULT_LAN_TRACKING
        )

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""

        OPTIONS_SCHEMA = vol.Schema(
            {vol.Required(CONF_LAN_TRACKING, default=self._lan_tracking): bool}
        )

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="user", data_schema=OPTIONS_SCHEMA)
