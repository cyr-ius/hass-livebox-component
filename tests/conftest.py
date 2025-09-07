"""The tests for the component."""

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    load_json_object_fixture,
)

from custom_components.livebox.const import (
    CONF_DISPLAY_DEVICES,
    CONF_LAN_TRACKING,
    CONF_TRACKING_TIMEOUT,
    CONF_WIFI_TRACKING,
    DEFAULT_DISPLAY_DEVICES,
    DEFAULT_LAN_TRACKING,
    DEFAULT_TRACKING_TIMEOUT,
    DEFAULT_WIFI_TRACKING,
    DOMAIN,
)

from .const import (
    MOCK_USER_INPUT,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for hass."""
    yield


@pytest.fixture(name="AIOSysbus")
def mock_router(request) -> Generator[MagicMock | AsyncMock]:
    """Mock a successful connection."""
    model = getattr(request, "param", "7")  # valeur par défaut

    # "Livebox 3": "Livebox 3", 3
    # "Livebox 4": "Livebox 4", 4
    # "Livebox Fibre": "Livebox 5", 5
    # "Livebox 6": "Livebox 6", 6
    # "Livebox 7": "Livebox 7", 7
    # "Livebox W7": "Livebox W7", 7.1
    # "Livebox Nautilus": "Livebox S", 7.2
    # "Livebox S": "Livebox S", 7.2

    if model == "5":
        api = load_json_object_fixture("Livebox Fibre.json")["api_raw"]
    elif model == "7":
        api = load_json_object_fixture("Livebox 7.json")["api_raw"]
    elif model == "7.1":
        api = load_json_object_fixture("Livebox W7.json")["api_raw"]
    else:
        raise ValueError(f"Unknown model: {model}")

    with patch("custom_components.livebox.coordinator.AIOSysbus") as mock:
        instance = mock.return_value
        instance.async_connect = AsyncMock(return_value=True)
        instance.async_get_permissions = AsyncMock(
            return_value=api["AIOSysbus.async_get_permissions"]
        )
        instance.deviceinfo.async_get_deviceinfo = AsyncMock(
            return_value=api["DeviceInfo.async_get_deviceinfo"]
        )

        def _mock_get_devices(*args, **kwargs):
            """Mock for async_get_devices to return different values based on first arg."""

            def _filtered_devices():
                filtered_devices = {"status": {"eth": [], "wifi": []}}
                for device in api["Devices.async_get_devices"]["status"]:
                    if (
                        ("edev" in device["Tags"] or "hnid" in device["Tags"])
                        and "wifi" in device["Tags"]
                        and device["PhysAddress"] is not None
                    ):
                        filtered_devices["status"]["wifi"].append(device)
                return filtered_devices

            def _filtered_interfaces():
                filtered_interfaces = {"status": {"eth": [], "wifi": []}}
                for device in api["Devices.async_get_devices"]["status"]:
                    if "self" in device["Tags"] and "vap" in device["Tags"]:
                        filtered_interfaces["status"]["wifi"].append(device)
                    if "self" in device["Tags"] and "eth" in device["Tags"]:
                        filtered_interfaces["status"]["eth"].append(device)
                return filtered_interfaces

            if len(args) == 0:
                return api["Devices.async_get_devices"]
            if args[0] == {"expression": {"wifi": "vap && lan", "eth": "eth && lan"}}:
                return _filtered_interfaces()
            if args[0] == {
                "expression": {
                    "wifi": 'wifi && (edev || hnid) and .PhysAddress!=""',
                    "eth": 'eth && (edev || hnid) and .PhysAddress!=""',
                }
            }:
                return _filtered_devices()

            if args[0] == {
                "expression": {
                    "wifi": '.Active==true && wifi && (edev || hnid) and .PhysAddress!=""',
                    "eth": '.Active==true && eth && (edev || hnid) and .PhysAddress!=""',
                }
            }:
                return _filtered_devices()

            return {}

        instance.devices.async_get_devices = AsyncMock(side_effect=_mock_get_devices)

        instance.voiceservice.async_get_calllist = AsyncMock(
            return_value=api["VoiceService.async_get_calllist"]
        )
        instance.voiceservice.async_ring = AsyncMock()
        instance.nemo.async_lucky_addr_address_lan = AsyncMock(
            return_value=api["NeMo.async_lucky_addr_address::lan"]
        )
        instance.nemo.async_lucky_addr_address_data = AsyncMock(
            return_value=api["NeMo.async_lucky_addr_address::data"]
        )

        def _mock_get_mibs(*args, **kwargs):
            """Mock for async_get_MIBs to return different values based on first arg."""
            if args[0] == "data":
                return api["NeMo.async_get_MIBs::data"]
            if args[0] == "lan":
                if args[1] == {"mibs": "wlanvap"}:
                    return {
                        "status": api["NeMo.async_get_MIBs::lan"]["status"]["wlanvap"]
                    }
                return api["NeMo.async_get_MIBs::lan"]
            if args[0] == "veip0":
                return api["NeMo.async_get_MIBs::veip0"]
            return {}

        instance.nemo.async_get_MIBs = AsyncMock(side_effect=_mock_get_mibs)

        def _mock_get_net_dev_stats(*args, **kwargs):
            """Mock for async_get_net_dev_stats to return different values based on first arg."""
            if args[0] == "eth0":
                return api["NeMo.async_get_net_dev_stats::eth0"]
            if args[0] == "veip0":
                return api["NeMo.async_get_net_dev_stats::veip0"]
            return {}

        instance.nemo.async_get_net_dev_stats = AsyncMock(
            side_effect=_mock_get_net_dev_stats
        )
        instance.nemo.async_get_dsl0_line_stats = AsyncMock(
            return_value=api["NeMo.async_get_dsl0_line_stats"]
        )
        instance.nemo.async_wifi = AsyncMock()

        instance.sfp.async_get = AsyncMock(return_value=api["SFP.async_get"])

        def _mock_get_schedule(*args, **kwargs):
            """Mock for async_get_schedule to return different values based on first arg."""
            return {}

        instance.schedule.async_get_schedule = AsyncMock(side_effect=_mock_get_schedule)

        instance.schedule.async_get_scheduletypes = AsyncMock(
            return_value=api["Schedule.async_get_scheduletypes"]
        )
        instance.dhcp.async_get_dhcp_pool = AsyncMock(
            return_value=api["Dhcp.async_get_dhcp_pool"]
        )
        instance.dhcp.async_get_dhcp_stats = AsyncMock(
            return_value=api.get("Dhcp.async_get_dhcp_stats", {})
        )
        instance.dhcp.async_get_dhcp6_status = AsyncMock(
            return_value=api["Dhcp.async_get_dhcp6_status"]
        )

        def _mock_dhcp_leases(*args, **kwargs):
            """Mock for async_get_dhcp_leases to return different values based on first arg."""
            if args[1] == "default":
                return api.get("Dhcp.async_get_dhcp_leases", {})
            if args[1] == "guest":
                return api.get("Dhcp.async_get_dhcp_leases::guest", {})
            return {}

        instance.dhcp.async_get_dhcp_leases = AsyncMock(side_effect=_mock_dhcp_leases)

        instance.dyndns.async_get_hosts = AsyncMock(
            return_value=api["DynDNS.async_get_hosts"]
        )
        instance.dyndns.async_get_services = AsyncMock(
            return_value=api["DynDNS.async_get_services"]
        )
        instance.dyndns.async_get_global_enable = AsyncMock(
            return_value=api["DynDNS.async_get_global_enable"]
        )
        # instance.event.async_get_events = AsyncMock(return_value=INFO)  # take 10s
        instance.userinterface.async_get_language = AsyncMock(
            return_value=api["UserInterface.async_get_language"]
        )
        instance.userinterface.async_get_state = AsyncMock(
            return_value=api["UserInterface.async_get_state"]
        )
        instance.upnpigd.async_get = AsyncMock(return_value=api["UPnPIGD.async_get"])
        instance.homelan.async_get_results = AsyncMock(
            return_value=api.get("HomeLan.async_get_results", {})
        )
        # instance.homelan.async_get_devices_results = AsyncMock(return_value=INFO)  # take 13s
        instance.homelan.async_get_maxnumber_records = AsyncMock(
            return_value=api["HomeLan.async_get_maxnumber_records"]
        )
        instance.homelan.async_get_reading_interval = AsyncMock(
            return_value=api["HomeLan.async_get_reading_interval"]
        )
        instance.homelan.async_get_devices_reading_interval = AsyncMock(
            return_value=api["HomeLan.async_get_devices_reading_interval"]
        )
        instance.homelan.async_get_devices_status = AsyncMock(
            return_value=api["HomeLan.async_get_devices_status"]
        )
        instance.screen.async_get_show_wifi_password = AsyncMock(
            return_value=api["Screen.async_get_show_wifi_password"]
        )
        instance.pnp.async_get = AsyncMock(return_value=api["PnP.async_get"])
        instance.iotservice.async_get_status = AsyncMock(
            return_value=api["IoTService.async_get_status"]
        )
        instance.time.async_get_time = AsyncMock(
            return_value=api["Time.async_get_time"]
        )
        instance.time.async_get_utctime = AsyncMock(
            return_value=api["Time.async_get_utctime"]
        )
        instance.time.async_get_status = AsyncMock(
            return_value=api["Time.async_get_status"]
        )
        instance.time.async_get_ntp = AsyncMock(return_value=api["Time.async_get_ntp"])
        instance.time.async_get_localtime_zonename = AsyncMock(
            return_value=api["Time.async_get_localtime_zonename"]
        )
        instance.nmc.async_get = AsyncMock(return_value=api["Nmc.async_get"])
        instance.nmc.async_get_wifi = AsyncMock(return_value=api["Nmc.async_get_wifi"])
        instance.nmc.async_get_guest_wifi = AsyncMock(
            return_value=api["Nmc.async_get_guest_wifi"]
        )
        instance.nmc.async_get_wifi_stats = AsyncMock(
            return_value=api["Nmc.async_get_wifi_stats"]
        )
        instance.nmc.async_get_lan_ip = AsyncMock(
            return_value=api["Nmc.async_get_lan_ip"]
        )
        instance.nmc.async_get_wanmodelist = AsyncMock(
            return_value=api["Nmc.async_get_wanmodelist"]
        )
        instance.nmc.async_get_wan_status = AsyncMock(
            return_value=api["Nmc.async_get_wan_status"]
        )
        instance.nmc.async_update_versioninfo = AsyncMock(
            return_value=api["Nmc.async_update_versioninfo"]
        )
        instance.nmc.async_get_network = AsyncMock(
            return_value=api["Nmc.async_get_network"]
        )
        instance.nmc.async_get_iptv_status = AsyncMock(
            return_value=api["Nmc.async_get_iptv_status"]
        )
        instance.nmc.async_get_iptv_config = AsyncMock(
            return_value=api["Nmc.async_get_iptv_config"]
        )
        instance.nmc.async_get_iptv_multi_screens = AsyncMock(
            return_value=api["Nmc.async_get_iptv_multi_screens"]
        )
        instance.nmc.async_autodetect = AsyncMock(
            return_value=api["Nmc.async_autodetect"]
        )
        instance.nmc.async_get_remote_access = AsyncMock(
            return_value=api["Nmc.async_get_remote_access"]
        )
        instance.nmc.async_reboot = AsyncMock()
        instance.nmc.async_set_wifi = AsyncMock()
        instance.nmc.async_guest_wifi = AsyncMock()

        instance.usermanagement.async_get_users = AsyncMock(
            return_value=api["UserManagement.async_get_users"]
        )
        instance.usermanagement.async_get_groups = AsyncMock(
            return_value=api["UserManagement.async_get_groups"]
        )
        instance.remoteaccess.async_get = AsyncMock(
            return_value=api["RemoteAccess.async_get"]
        )
        instance.orangeremoteaccess.async_get = AsyncMock(
            return_value=api["OrangeRemoteAccess.async_get"]
        )
        instance.speedtest.async_get_wan_results = AsyncMock(
            return_value=api["SpeedTest.async_get_wan_results"]
        )
        instance.sgcomci.async_get_optical = AsyncMock(return_value={})  # Livebox 5656

        instance.firewall.async_get_protocol_forwarding = AsyncMock(
            return_value=api["Firewall.async_get_protocol_forwarding"]
        )
        instance.firewall.async_get_port_forwarding = AsyncMock(
            return_value=api["Firewall.async_get_port_forwarding"]
        )

        instance.close = AsyncMock()

        type(instance).__devices = PropertyMock(
            return_value=api["Devices.async_get_devices"]
        )
        type(instance).__model = PropertyMock(return_value=model)
        type(instance).__unique_name = PropertyMock(
            return_value=slugify(
                api["DeviceInfo.async_get_deviceinfo"]["status"]["ProductClass"]
            )
        )

        yield instance


@pytest.fixture(name="config_entry")
def get_config_entry(hass: HomeAssistant) -> ConfigEntry:
    """Create and register mock config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=MOCK_USER_INPUT,
        unique_id="012345678901234",
        options={
            CONF_WIFI_TRACKING: DEFAULT_WIFI_TRACKING,
            CONF_LAN_TRACKING: DEFAULT_LAN_TRACKING,
            CONF_TRACKING_TIMEOUT: DEFAULT_TRACKING_TIMEOUT,
            CONF_DISPLAY_DEVICES: DEFAULT_DISPLAY_DEVICES,
        },
        title="Livebox X (012345678901234)",
    )
    config_entry.add_to_hass(hass)
    return config_entry
