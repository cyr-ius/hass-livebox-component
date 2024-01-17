"""Diagnostics support for Livebox."""
from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
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
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

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

    diag(coordinator.api.get_permissions)
    diag(coordinator.api.call.get_voiceapplication_calllist)
    diag(coordinator.api.connection.get_lan_luckyAddrAddress)
    diag(coordinator.api.connection.get_data_luckyAddrAddress)
    diag(coordinator.api.connection.get_lo_DHCPOption)
    diag(coordinator.api.connection.get_dsl0_DSLStats)
    diag(coordinator.api.connection.get_dsl0_MIBS)
    diag(coordinator.api.connection.get_data_MIBS)
    diag(coordinator.api.connection.get_lan_MIBS)
    diag(coordinator.api.system.get_nmc)
    diag(coordinator.api.wifi.get_wifi)
    diag(coordinator.api.guestwifi.get_guest_wifi)
    diag(coordinator.api.schedule.get_schedule)
    diag(coordinator.api.devices.get_devices)
    diag(coordinator.api.devices.get_devices_config1)
    diag(coordinator.api.dhcp.get_dhcp_pool)
    diag(coordinator.api.dhcp.get_dhcp_stats)
    diag(coordinator.api.dhcp.get_dhcp_config)
    diag(coordinator.api.dhcp.get_dhcp6_status)
    diag(coordinator.api.ddns.get_hosts)
    diag(coordinator.api.ddns.get_services)
    diag(coordinator.api.ddns.get_ddns)
    diag(coordinator.api.event.get_events)
    diag(coordinator.api.userinterface.getLanguage)
    diag(coordinator.api.userinterface.getState)
    diag(coordinator.api.userinterface.getDebugInformation)
    diag(coordinator.api.nat.get_upnp_devices)
    diag(coordinator.api.wifi.get_wifi)
    diag(coordinator.api.wifi.get_wifi_Stats)
    diag(coordinator.api.wifi.get_openmode_status)
    diag(coordinator.api.wifi.get_securemode_status)
    diag(coordinator.api.lan.get_lan)
    diag(coordinator.api.lan.get_lan_interfaces)
    diag(coordinator.api.lan.get_lan_maxnumber)
    diag(coordinator.api.lan.get_lan_interval)
    diag(coordinator.api.lan.get_lan_status)
    diag(coordinator.api.lan.get_devices_results)
    diag(coordinator.api.lan.get_lan_ip)
    diag(coordinator.api.guestwifi.get_guest_wifi)
    diag(coordinator.api.schedule.get_scheduletypes)
    diag(coordinator.api.schedule.get_schedules)
    diag(coordinator.api.schedule.get_completeschedules)
    diag(coordinator.api.screen.getShowWifiPassword)
    diag(coordinator.api.profile.get_profile)
    diag(coordinator.api.profile.get_profile_data)
    diag(coordinator.api.profile.get_profile_current)
    diag(coordinator.api.datahub.get_datahub)
    diag(coordinator.api.datahub.get_datahub_users)
    diag(coordinator.api.locations.get_locations_domain)
    diag(coordinator.api.locations.get_locations)
    diag(coordinator.api.locations.get_locations_composition)
    diag(coordinator.api.usbhosts.get_usb_devices)
    diag(coordinator.api.system.get_led)
    diag(coordinator.api.system.get_pnp)
    diag(coordinator.api.system.get_remoteaccess)
    diag(coordinator.api.system.get_remoteaccess_timeleft)
    diag(coordinator.api.system.get_iot_service)
    diag(coordinator.api.system.get_probe)
    diag(coordinator.api.system.get_time)
    diag(coordinator.api.system.get_utctime)
    diag(coordinator.api.system.get_time_status)
    diag(coordinator.api.system.get_time_ntp)
    diag(coordinator.api.system.get_time_localtime_zonename)
    diag(coordinator.api.system.get_nmc)
    diag(coordinator.api.system.get_wanmodelist)
    diag(coordinator.api.system.get_wanstatus)
    diag(coordinator.api.system.get_versioninfo)
    diag(coordinator.api.system.get_datatracking)
    diag(coordinator.api.system.get_guest)
    diag(coordinator.api.system.get_led_status)
    diag(coordinator.api.system.get_networkconfig)
    diag(coordinator.api.system.get_orangetv_IPTVStatus)
    diag(coordinator.api.system.get_orangetv_IPTVConfig)
    diag(coordinator.api.system.get_orangetv_IPTVMultiScreens)
    diag(coordinator.api.system.get_profiles)
    diag(coordinator.api.system.get_autodetect)
    diag(coordinator.api.system.get_acs)
    diag(coordinator.api.system.get_wlantimer)
    diag(coordinator.api.system.get_hosts)
    diag(coordinator.api.usermanagement.get_users)
    diag(coordinator.api.usermanagement.get_groups)
    diag(coordinator.api.usermanagement.get_logincounters)

    return {
        "device_id": coordinator.unique_id,
        "entry": {
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "data": async_redact_data(coordinator.data, TO_REDACT),
        "api_raw": api_raw,
    }
