"""Diagnostics support for Livebox."""
from __future__ import annotations

import logging
from time import time
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import COORDINATOR, DOMAIN, LIVEBOX_API, LIVEBOX_ID

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
}

_LOGGER = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    datas = hass.data[DOMAIN][entry.entry_id]
    box_id = datas[LIVEBOX_ID]
    api = datas[LIVEBOX_API]
    coordinator = datas[COORDINATOR]

    api_methods = [
        api.get_permissions,
        api.call.get_voiceapplication_calllist,
        api.connection.get_lan_luckyAddrAddress,
        api.connection.get_data_luckyAddrAddress,
        # api.connection.get_lo_DHCPOption,  # Exception: [{'error': 196638, 'description': 'Mandatory argument missing', 'info': 'type'}, {'error': 196639, 'description': 'Function execution failed', 'info': 'getDHCPOption'}]
        # api.connection.get_dsl0_DSLStats,  # Exception: [{'error': 196618, 'description': 'Object or parameter not found', 'info': 'NeMo.Intf.dsl0'}]
        # api.connection.get_dsl0_MIBS,  # Exception: [{'error': 196618, 'description': 'Object or parameter not found', 'info': 'NeMo.Intf.dsl0'}]
        api.connection.get_data_MIBS,
        api.connection.get_lan_MIBS,
        api.system.get_nmc,
        api.wifi.get_wifi,
        api.guestwifi.get_guest_wifi,
        # api.schedule.get_schedule,  # Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'type'}, {'error': 196640, 'description': 'Missing mandatory argument', 'info': 'ID'}]
        api.devices.get_devices,
        # api.devices.get_devices_config,  # Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'module'}, {'error': 196640, 'description': 'Missing mandatory argument', 'info': 'option'}]
        api.dhcp.get_dhcp_pool,
        api.dhcp.get_dhcp_stats,
        api.dhcp.get_dhcp_config,
        api.dhcp.get_dhcp6_status,
        api.dyndns.get_hosts,
        api.dyndns.get_services,
        api.dyndns.get_ddns,
        # api.event.get_events,  # take 10s
        api.userinterface.getLanguage,
        api.userinterface.getState,
        # api.userinterface.getDebugInformation,  Exception: [{'error': 196636, 'description': 'Function is not implemented', 'info': 'getDebugInformation'}]
        api.nat.get_upnp_devices,
        api.wifi.get_wifi,
        api.wifi.get_wifi_Stats,
        api.wifi.get_openmode_status,
        api.wifi.get_securemode_status,
        # api.lan.get_lan,  # take 5s
        # api.lan.get_lan_interfaces,  # Exception: [{'error': 196618, 'description': 'Object or parameter not found', 'info': 'getInterfacesName'}]
        api.lan.get_lan_maxnumber,
        api.lan.get_lan_interval,
        api.lan.get_lan_status,
        # api.lan.get_devices_results,  # take 13s
        api.lan.get_lan_ip,
        api.guestwifi.get_guest_wifi,
        api.schedule.get_scheduletypes,
        # api.schedule.get_schedules,  # Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'type'}]
        # api.schedule.get_completeschedules,  # Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'type'}]
        api.screen.getShowWifiPassword,
        # api.profiles.get_profile,  # Exception: [{'error': 196635, 'description': 'Function can not be executed for the specified object', 'info': 'get'}]
        # api.profiles.get_profile_data,  # Exception: [{'error': 196635, 'description': 'Function can not be executed for the specified object', 'info': 'getData'}]
        # api.profiles.get_profile_current,  # Exception: [{'error': 196618, 'description': 'Object or parameter not found', 'info': 'getCurrent'}]
        api.datahub.get_datahub,
        api.datahub.get_datahub_users,
        # api.locations.get_locations_domain,  # Exception: Locations.get_locations_domain() missing 1 required positional argument: 'conf'
        # api.locations.get_locations,  # Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'location'}]
        # api.locations.get_locations_composition,  #Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'location'}]
        # api.usbhosts.get_usb_devices,  # Exception: [{'error': 13, 'description': 'Permission denied', 'info': 'USBHosts'}]
        api.system.get_led,
        api.system.get_pnp,
        api.system.get_remoteaccess,
        api.system.get_remoteaccess_timeleft,
        api.system.get_iot_service,
        # api.system.get_probe,  # Exception: [{'error': 196618, 'description': 'Object or parameter not found', 'info': 'getStatus'}]
        api.system.get_time,
        api.system.get_utctime,
        api.system.get_time_status,
        api.system.get_time_ntp,
        api.system.get_time_localtime_zonename,
        api.system.get_nmc,
        api.system.get_wanmodelist,
        api.system.get_wanstatus,
        api.system.get_versioninfo,
        api.system.get_datatracking,
        api.system.get_guest,
        # api.system.get_led_status,  # Exception: [{'error': 196640, 'description': 'Missing mandatory argument', 'info': 'name'}]
        api.system.get_networkconfig,
        api.system.get_orangetv_IPTVStatus,
        api.system.get_orangetv_IPTVConfig,
        api.system.get_orangetv_IPTVMultiScreens,
        api.system.get_profiles,
        api.system.get_autodetect,
        # api.system.get_acs,  # Exception: [{'error': 13, 'description': 'Permission denied', 'info': 'NMC.ACS'}]
        # api.system.get_wlantimer,  # Exception: [{'error': 1245185, 'description': 'Interface name is not a valid name', 'info': ''}, {'error': 196639, 'description': 'Function execution failed', 'info': 'getActivationTimer'}]
        api.system.get_hosts,
        api.usermanagement.get_users,
        api.usermanagement.get_groups,
        # api.usermanagement.get_logincounters,  # Exception: [{'error': 13, 'description': 'Permission denied', 'info': 'UserManagement.LoginCounters'}]
    ]

    _LOGGER.debug("Start building diagnostics data...")
    start_time = time()
    api_raw = {}
    for api_method in api_methods:
        try:
            _LOGGER.debug("Call API %s method...", api_method.__qualname__)
            result = await hass.async_add_executor_job(api_method)
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
        except Exception as err:
            api_raw[api_method.__qualname__] = f"Exception: {err}"
    _LOGGER.debug("Diagnostics data builded in %0.1fs", time() - start_time)

    return {
        "box_id": box_id,
        "entry": {
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "data": async_redact_data(coordinator.data, TO_REDACT),
        "api_raw": api_raw,
    }
