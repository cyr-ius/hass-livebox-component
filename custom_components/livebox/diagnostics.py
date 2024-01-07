"""Diagnostics support for Livebox."""
from __future__ import annotations

from contextlib import suppress
from typing import Any, Callable

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


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    datas = hass.data[DOMAIN][entry.entry_id]
    box_id = datas[LIVEBOX_ID]
    api = datas[LIVEBOX_API]
    coordinator = datas[COORDINATOR]

    api_raw = {}

    async def diag(func: Callable[..., Any], *args: Any) -> None:
        rslt = {}
        with suppress(Exception):
            rsp = func(*args)
            rslt = (
                rsp
                if isinstance(rsp, dict | list | set | float | int | str | tuple)
                else vars(rsp)
            )

        api_raw.update({func.__name__: rslt})

    diag(api.get_permissions)
    diag(api.call.get_voiceapplication_calllist)
    diag(api.connection.get_lan_luckyAddrAddress)
    diag(api.connection.get_data_luckyAddrAddress)
    diag(api.connection.get_lo_DHCPOption)
    diag(api.connection.get_dsl0_DSLStats)
    diag(api.connection.get_dsl0_MIBS)
    diag(api.connection.get_data_MIBS)
    diag(api.connection.get_lan_MIBS)
    diag(api.system.get_nmc)
    diag(api.wifi.get_wifi)
    diag(api.guestwifi.get_guest_wifi)
    diag(api.schedule.get_schedule)
    diag(api.devices.get_devices)
    diag(api.devices.get_devices_config1)
    diag(api.dhcp.get_dhcp_pool)
    diag(api.dhcp.get_dhcp_stats)
    diag(api.dhcp.get_dhcp_config)
    diag(api.dhcp.get_dhcp6_status)
    diag(api.ddns.get_hosts)
    diag(api.ddns.get_services)
    diag(api.ddns.get_ddns)
    diag(api.event.get_events)
    diag(api.userinterface.getLanguage)
    diag(api.userinterface.getState)
    diag(api.userinterface.getDebugInformation)
    diag(api.nat.get_upnp_devices)
    diag(api.wifi.get_wifi)
    diag(api.wifi.get_wifi_Stats)
    diag(api.wifi.get_openmode_status)
    diag(api.wifi.get_securemode_status)
    diag(api.lan.get_lan)
    diag(api.lan.get_lan_interfaces)
    diag(api.lan.get_lan_maxnumber)
    diag(api.lan.get_lan_interval)
    diag(api.lan.get_lan_status)
    diag(api.lan.get_devices_results)
    diag(api.lan.get_lan_ip)
    diag(api.guestwifi.get_guest_wifi)
    diag(api.schedule.get_scheduletypes)
    diag(api.schedule.get_schedules)
    diag(api.schedule.get_completeschedules)
    diag(api.screen.getShowWifiPassword)
    diag(api.profile.get_profile)
    diag(api.profile.get_profile_data)
    diag(api.profile.get_profile_current)
    diag(api.datahub.get_datahub)
    diag(api.datahub.get_datahub_users)
    diag(api.locations.get_locations_domain)
    diag(api.locations.get_locations)
    diag(api.locations.get_locations_composition)
    diag(api.usbhosts.get_usb_devices)
    diag(api.system.get_led)
    diag(api.system.get_pnp)
    diag(api.system.get_remoteaccess)
    diag(api.system.get_remoteaccess_timeleft)
    diag(api.system.get_iot_service)
    diag(api.system.get_probe)
    diag(api.system.get_time)
    diag(api.system.get_utctime)
    diag(api.system.get_time_status)
    diag(api.system.get_time_ntp)
    diag(api.system.get_time_localtime_zonename)
    diag(api.system.get_nmc)
    diag(api.system.get_wanmodelist)
    diag(api.system.get_wanstatus)
    diag(api.system.get_versioninfo)
    diag(api.system.get_datatracking)
    diag(api.system.get_guest)
    diag(api.system.get_led_status)
    diag(api.system.get_networkconfig)
    diag(api.system.get_orangetv_IPTVStatus)
    diag(api.system.get_orangetv_IPTVConfig)
    diag(api.system.get_orangetv_IPTVMultiScreens)
    diag(api.system.get_profiles)
    diag(api.system.get_autodetect)
    diag(api.system.get_acs)
    diag(api.system.get_wlantimer)
    diag(api.system.get_hosts)
    diag(api.usermanagement.get_users)
    diag(api.usermanagement.get_groups)
    diag(api.usermanagement.get_logincounters)

    return {
        "box_id": box_id,
        "entry": {
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "data": async_redact_data(coordinator.data, TO_REDACT),
        "api_raw": api_raw,
    }