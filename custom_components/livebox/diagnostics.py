"""Diagnostics support for Livebox."""

from __future__ import annotations

import logging
from time import time
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

TO_REDACT = {
    "address",
    "Address",
    "api_key",
    "AuthenticationInformation",
    "BaseMAC",
    "BSSID",
    "callDestination",
    "callOrigin",
    "city",
    "ClientID",
    "ConnectionIPv4Address",
    "ConnectionIPv6Address",
    "country",
    "date",
    "dateOfBirth",
    "DestinationIPAddress",
    "DestinationMACAddress",
    "DHCPMaxAddress",
    "DHCPMinAddress",
    "DHCPServer",
    "DHCPv4ServerMaxAddress",
    "DHCPv4ServerMinAddress",
    "DHCPv4ServerNetmask",
    "Dst",
    "DUID",
    "email",
    "ExternalIPAddress",
    "firstName",
    "FirstName",
    "Gateway",
    "host",
    "hostname",
    "Id",
    "imei",
    "ip4_addr",
    "ip6_addr",
    "IPAddress",
    "IPRouters",
    "IPRouters",
    "IPv6Address",
    "IPv6DelegatedPrefix",
    "Key",
    "KeyPassPhrase",
    "lastName",
    "LastName",
    "lat",
    "latitude",
    "LLAddress",
    "lon",
    "longitude",
    "MacAddress",
    "MACAddress",
    "MACADDRESS",
    "MACVendor",
    "MaxAddress",
    "MinAddress",
    "MobilePhoneNumber",
    "Netmask",
    "nickname",
    "Owner",
    "password",
    "phone_number",
    "phone",
    "PhysAddress",
    "placeOfBirth",
    "PreSharedKey",
    "ProvisioningCode",
    "RadiusSecret",
    "RadiusServerIPAddr",
    "RemoteGateway",
    "remoteName",
    "remoteNumber",
    "SAEPassphrase",
    "SelfPIN",
    "SelfPIN",
    "serial",
    "SerialNumber",
    "SourceMACAddress",
    "SSID",
    "ssid",
    "SubnetMask",
    "system_serial",
    "terminal",
    "trunkLineNumber",
    "UniqueID",
    "username",
    "Username",
    "UUID",
    "VLANID",
    "WEPKey",
}

_LOGGER = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    # Only dump devices with a MAC address
    params = {
        "expression": {
            "wifi": 'wifi && (edev || hnid) and .PhysAddress!=""',
            "eth": 'eth && (edev || hnid) and .PhysAddress!=""',
        }
    }

    end_time = int(time())
    start_time = end_time - 60

    api_methods = [
        coordinator.api.async_get_permissions,
        coordinator.api.deviceinfo.async_get_deviceinfo,
        coordinator.api.voiceservice.async_get_calllist,
        (coordinator.api.nemo.async_lucky_addr_address, ["lan"]),
        (coordinator.api.nemo.async_lucky_addr_address, ["data"]),
        (coordinator.api.nemo.async_get_MIBs, ["data"]),
        (coordinator.api.nemo.async_get_MIBs, ["lan"]),
        (coordinator.api.nemo.async_get_MIBs, ["veip0"]),
        (
            coordinator.api.nemo.async_get_MIBs,
            ["lan", {"mibs": "base eth"}],
        ),
        (
            coordinator.api.nemo.async_get_MIBs,
            ["guest", {"mibs": "base wlanradio wlanvap"}],
        ),
        (
            coordinator.api.nemo.async_get_MIBs,
            ["lan", {"mibs": "base wlanradio wlanvap"}],
        ),
        (coordinator.api.nemo.async_get_net_dev_stats, ["ETH0"]),
        (coordinator.api.nemo.async_get_net_dev_stats, ["ETH1"]),
        (coordinator.api.nemo.async_get_net_dev_stats, ["ETH2"]),
        (coordinator.api.nemo.async_get_net_dev_stats, ["veip0"]),
        (coordinator.api.nemo.async_get_net_dev_stats, ["vap2g0priv"]),
        (coordinator.api.nemo.async_get_net_dev_stats, ["vap5g0priv"]),
        coordinator.api.nemo.async_get_dsl0_line_stats,
        coordinator.api.sfp.async_get,
        coordinator.api.firewall.async_get_protocol_forwarding,
        coordinator.api.firewall.async_get_port_forwarding,
        coordinator.api.upnpigd.async_get,
        coordinator.api.schedule.async_get_scheduletypes,
        coordinator.api.dhcp.async_get_dhcp_pool,
        coordinator.api.dhcp.async_get_dhcp_leases,
        (coordinator.api.dhcp.async_get_dhcp_leases, [None, "guest"]),
        coordinator.api.dhcp.async_get_dhcp_staticleases,
        # coordinator.api.dhcp.async_get_dhcp_stats,
        coordinator.api.dhcp.async_get_dhcp6_status,
        coordinator.api.dyndns.async_get_hosts,
        coordinator.api.dyndns.async_get_services,
        coordinator.api.dyndns.async_get_global_enable,
        # coordinator.api.event.async_get_events,  # take 10s
        coordinator.api.userinterface.async_get_language,
        coordinator.api.userinterface.async_get_state,
        coordinator.api.upnpigd.async_get,
        coordinator.api.homelan.async_get_interface,
        # coordinator.api.homelan.async_get_results,  # take 5s
        # coordinator.api.homelan.async_get_devices_results,  # take 13s
        coordinator.api.homelan.async_get_maxnumber_records,
        coordinator.api.homelan.async_get_reading_interval,
        coordinator.api.homelan.async_get_devices_reading_interval,
        coordinator.api.homelan.async_get_devices_status,
        coordinator.api.screen.async_get_show_wifi_password,
        coordinator.api.pnp.async_get,
        coordinator.api.iotservice.async_get_status,
        coordinator.api.time.async_get_time,
        coordinator.api.time.async_get_utctime,
        coordinator.api.time.async_get_status,
        coordinator.api.time.async_get_ntp,
        coordinator.api.time.async_get_localtime_zonename,
        coordinator.api.nmc.async_get,
        coordinator.api.nmc.async_get_wifi,
        coordinator.api.nmc.async_get_guest_wifi,
        coordinator.api.nmc.async_get_wifi_stats,
        coordinator.api.nmc.async_get_lan_ip,
        coordinator.api.nmc.async_get_wanmodelist,
        coordinator.api.nmc.async_get_wan_status,
        coordinator.api.nmc.async_update_versioninfo,
        coordinator.api.nmc.async_get_network,
        coordinator.api.nmc.async_get_iptv_status,
        coordinator.api.nmc.async_get_iptv_config,
        coordinator.api.nmc.async_get_iptv_multi_screens,
        coordinator.api.nmc.async_autodetect,
        coordinator.api.nmc.async_get_wan_status,
        coordinator.api.nmc.async_get_remote_access,
        coordinator.api.usermanagement.async_get_users,
        coordinator.api.usermanagement.async_get_groups,
        coordinator.api.remoteaccess.async_get,
        coordinator.api.orangeremoteaccess.async_get,
        coordinator.api.speedtest.async_get_wan_results,
        coordinator.api.devices.async_get_devices,
        (
            coordinator.api.devices.async_get_devices,
            [
                {
                    "expression": {
                        "wifi": 'wifi && (edev || hnid) and .PhysAddress!=""',
                        "eth": 'eth && (edev || hnid) and .PhysAddress!=""',
                    }
                }
            ],
        ),
        (
            coordinator.api.devices.async_get_devices,
            [
                {
                    "expression": {
                        "wifi": "lan && vap && .Active==True",
                        "eth": "lan && eth && .Active==True",
                    }
                }
            ],
        ),
    ]

    _LOGGER.debug("Start building diagnostics data...")
    start_time = time()
    api_raw = {}
    for api_method in api_methods:
        params = None
        try:
            if isinstance(api_method, tuple):
                api_method, params = api_method
                str_p = "_".join(str(e) for e in params)
                qualified_name = f"{api_method.__qualname__}::{str_p}"
            else:
                qualified_name = api_method.__qualname__

            _LOGGER.debug("Call API %s method...", qualified_name)
            result = await api_method(*params) if params else await api_method()
            api_raw[qualified_name] = (
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
            api_raw[qualified_name] = f"Exception: {err}"
    _LOGGER.debug("Diagnostics data built in %0.1fs", time() - start_time)

    lucky_address = api_raw.get("NeMo.async_lucky_addr_address::lan", {})
    if isinstance(lucky_address, dict) and lucky_address.get("status"):
        api_raw["NeMo.async_lucky_addr_address::lan"]["status"] = "**REDACTED**"

    lucky_address = api_raw.get("NeMo.async_lucky_addr_address::data", {})
    if isinstance(lucky_address, dict) and lucky_address.get("status"):
        api_raw["NeMo.async_lucky_addr_address::data"]["status"] = "**REDACTED**"

    return {
        "entry": {
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "data": async_redact_data(coordinator.data, TO_REDACT),
        "api_raw": async_redact_data(api_raw, TO_REDACT),
    }
