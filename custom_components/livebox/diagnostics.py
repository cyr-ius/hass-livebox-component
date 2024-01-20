"""Diagnostics support for Livebox."""
from __future__ import annotations

import logging
from time import time
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {
    "address",
    "api_key",
    "city",
    "country",
    "email",
    "host",
    "imei",
    "ip4_addr",
    "ip6_addr",
    "lat",
    "latitude",
    "lon",
    "longitude",
    "password",
    "phone",
    "serial",
    "system_serial",
    "username",
    "firstName",
    "lastName",
    "dateOfBirth",
    "nickname",
    "placeOfBirth",
    "KeyPassPhrase",
}

_LOGGER = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    api_methods = [
        coordinator.api.async_get_permissions,
        coordinator.api.call.async_get_voiceapplication_calllist,
        coordinator.api.connection.async_get_lan_luckyAddrAddress,
        coordinator.api.connection.async_get_data_luckyAddrAddress,
        # coordinator.api.connection.async_get_lo_DHCPOption,  # Exception: [{'error': 196638, 'description': 'Mandatory argument missing', 'info': 'type'}, {'error': 196639, 'description': 'Function execution failed', 'info': 'getDHCPOption'}]
        # coordinator.api.connection.async_get_dsl0_DSLStats,  # Exception: [{'error': 196618, 'description': 'Object or parameter not found', 'info': 'NeMo.Intf.dsl0'}]
        # coordinator.api.connection.async_get_dsl0_MIBS,  # Exception: [{'error': 196618, 'description': 'Object or parameter not found', 'info': 'NeMo.Intf.dsl0'}]
        coordinator.api.connection.async_get_data_MIBS,
        coordinator.api.connection.async_get_lan_MIBS,  # return WLANs passkey as KeyPassPhrase
        coordinator.api.system.async_get_nmc,
        coordinator.api.wifi.async_get_wifi,
        coordinator.api.guestwifi.async_get_guest_wifi,
        # coordinator.api.schedule.async_get_schedule,  # Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'type'}, {'error': 196640, 'description': 'Missing mandatory argument', 'info': 'ID'}]
        coordinator.api.devices.async_get_devices,
        # coordinator.api.devices.async_get_devices_config,  # Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'module'}, {'error': 196640, 'description': 'Missing mandatory argument', 'info': 'option'}]
        coordinator.api.dhcp.async_get_dhcp_pool,
        coordinator.api.dhcp.async_get_dhcp_stats,
        coordinator.api.dhcp.async_get_dhcp_config,
        coordinator.api.dhcp.async_get_dhcp6_status,
        coordinator.api.dyndns.async_get_hosts,
        coordinator.api.dyndns.async_get_services,
        coordinator.api.dyndns.async_get_ddns,
        # coordinator.api.event.async_get_events,  # take 10s
        coordinator.api.userinterface.async_getLanguage,
        coordinator.api.userinterface.async_getState,
        # coordinator.api.userinterface.async_getDebugInformation,  Exception: [{'error': 196636, 'description': 'Function is not implemented', 'info': 'getDebugInformation'}]
        coordinator.api.nat.async_get_upnp_devices,
        coordinator.api.wifi.async_get_wifi,
        coordinator.api.wifi.async_get_wifi_Stats,
        coordinator.api.wifi.async_get_openmode_status,
        coordinator.api.wifi.async_get_securemode_status,
        # coordinator.api.lan.async_get_lan,  # take 5s
        # coordinator.api.lan.async_get_lan_interfaces,  # Exception: [{'error': 196618, 'description': 'Object or parameter not found', 'info': 'getInterfacesName'}]
        coordinator.api.lan.async_get_lan_maxnumber,
        coordinator.api.lan.async_get_lan_interval,
        coordinator.api.lan.async_get_lan_status,
        # coordinator.api.lan.async_get_devices_results,  # take 13s
        coordinator.api.lan.async_get_lan_ip,
        coordinator.api.guestwifi.async_get_guest_wifi,
        coordinator.api.schedule.async_get_scheduletypes,
        # coordinator.api.schedule.async_get_schedules,  # Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'type'}]
        # coordinator.api.schedule.async_get_completeschedules,  # Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'type'}]
        coordinator.api.screen.async_getShowWifiPassword,
        # coordinator.api.profiles.async_get_profile,  # Exception: [{'error': 196635, 'description': 'Function can not be executed for the specified object', 'info': 'get'}]
        # coordinator.api.profiles.async_get_profile_data,  # Exception: [{'error': 196635, 'description': 'Function can not be executed for the specified object', 'info': 'getData'}]
        # coordinator.api.profiles.async_get_profile_current,  # Exception: [{'error': 196618, 'description': 'Object or parameter not found', 'info': 'getCurrent'}]
        coordinator.api.datahub.async_get_datahub,
        coordinator.api.datahub.async_get_datahub_users,
        # coordinator.api.locations.async_get_locations_domain,  # Exception: Locations.get_locations_domain() missing 1 required positional argument: 'conf'
        # coordinator.api.locations.async_get_locations,  # Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'location'}]
        # coordinator.api.locations.async_get_locations_composition,  #Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'location'}]
        # coordinator.api.usbhosts.async_get_usb_devices,  # Exception: [{'error': 13, 'description': 'Permission denied', 'info': 'USBHosts'}]
        coordinator.api.system.async_get_led,
        coordinator.api.system.async_get_pnp,
        coordinator.api.system.async_get_remoteaccess,
        coordinator.api.system.async_get_remoteaccess_timeleft,
        coordinator.api.system.async_get_iot_service,
        # coordinator.api.system.async_get_probe,  # Exception: [{'error': 196618, 'description': 'Object or parameter not found', 'info': 'getStatus'}]
        coordinator.api.system.async_get_time,
        coordinator.api.system.async_get_utctime,
        coordinator.api.system.async_get_time_status,
        coordinator.api.system.async_get_time_ntp,
        coordinator.api.system.async_get_time_localtime_zonename,
        coordinator.api.system.async_get_nmc,
        coordinator.api.system.async_get_wanmodelist,
        coordinator.api.system.async_get_wanstatus,
        coordinator.api.system.async_get_versioninfo,
        coordinator.api.system.async_get_datatracking,
        coordinator.api.system.async_get_guest,
        # coordinator.api.system.async_get_led_status,  # Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'name'}]
        coordinator.api.system.async_get_networkconfig,
        coordinator.api.system.async_get_orangetv_IPTVStatus,
        coordinator.api.system.async_get_orangetv_IPTVConfig,
        coordinator.api.system.async_get_orangetv_IPTVMultiScreens,
        coordinator.api.system.async_get_profiles,
        coordinator.api.system.async_get_autodetect,
        # coordinator.api.system.async_get_acs,  # Exception: [{'error': 13, 'description': 'Permission denied', 'info': 'NMC.ACS'}]
        # coordinator.api.system.async_get_wlantimer,  # Exception: [{'error': 1245185, 'description': 'Interface name is not a valid name', 'info': ''}, {'error': 196639, 'description': 'Function execution failed', 'info': 'getActivationTimer'}]
        coordinator.api.system.async_get_hosts,
        coordinator.api.usermanagement.async_get_users,
        coordinator.api.usermanagement.async_get_groups,
        # coordinator.api.usermanagement.async_get_logincounters,  # Exception: [{'error': 13, 'description': 'Permission denied', 'info': 'UserManagement.LoginCounters'}]
    ]

    _LOGGER.debug("Start building diagnostics data...")
    start_time = time()
    api_raw = {}
    for api_method in api_methods:
        try:
            _LOGGER.debug("Call API %s method...", api_method.__qualname__)
            result = await api_method
            api_raw[api_method.__qualname__] = (
                result
                if isinstance(result, (dict, list, set, float, int, str, tuple))
                or result is None
                else (
                    vars(result)
                    if hasattr(result, "__dict__")
                    else f"Can't dump {str(type(result))} data"
                )
            )
        except Exception as err:  # pylint: disable=broad-exception-caught
            api_raw[api_method.__qualname__] = f"Exception: {err}"
    _LOGGER.debug("Diagnostics data builded in %0.1fs", time() - start_time)

    return {
        "entry": {
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "data": async_redact_data(coordinator.data, TO_REDACT),
        "api_raw": async_redact_data(api_raw, TO_REDACT),
    }
