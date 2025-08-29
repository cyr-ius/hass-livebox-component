"""The tests for the component."""

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    load_json_object_fixture,
)

from custom_components.livebox.const import DOMAIN

from .const import (
    CALLLIST,
    DEVICES,
    DHCP_POOL,
    DSL0_LINE_STATS,
    GROUPS,
    GUEST_WIFI,
    IOT_STATUS,
    LAN_IP,
    LANGUAGE,
    LOCALTIME_ZONE,
    MIBS_DATA,
    MIBS_LAN,
    MIBS_VEIP0,
    MOCK_USER_INPUT,
    NET_DEV_STATS_ETH0,
    NET_DEV_STATS_VEIP0,
    NMC_AUTODETECT,
    NMC_GET,
    NMC_IPTV,
    NMC_IPTV_CONFIG,
    NMC_IPTV_MULTI_SCREENS,
    NMC_NETWORK,
    NTP,
    ORANGE_REMOTE_ACCESS,
    PNP,
    REMOTE_ACCESS,
    SCHEDULETYPES,
    SFP,
    SPEEDTEST_INFOS,
    TIME,
    TIME_STATUS,
    UPNPNGID,
    USERS,
    UTCTIME,
    WAN_STATUS,
    WIFI,
    WIFI_STATS,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for hass."""
    yield


@pytest.fixture(name="AIOSysbus")
def mock_router(request) -> Generator[MagicMock | AsyncMock]:
    """Mock a successful connection."""
    model = getattr(request, "param", "7")  # valeur par défaut

    if model == "4":
        INFO = load_json_object_fixture("LB_4_deviceinfo.json")
    elif model == "5":
        INFO = load_json_object_fixture("LB_5_deviceinfo.json")
    elif model == "6":
        INFO = load_json_object_fixture("LB_6_deviceinfo.json")
    elif model == "7":
        INFO = load_json_object_fixture("LB_7_deviceinfo.json")
    elif model == "w7":
        INFO = load_json_object_fixture("LB_W7_deviceinfo.json")
    else:
        raise ValueError(f"Unknown model: {model}")

    with patch("custom_components.livebox.coordinator.AIOSysbus") as mock:
        instance = mock.return_value
        type(instance).__model = PropertyMock(return_value=model)
        instance.async_connect = AsyncMock(return_value=True)
        instance.async_get_permissions = AsyncMock(return_value="http,admin")
        instance.deviceinfo.async_get_deviceinfo = AsyncMock(return_value=INFO)
        instance.devices.async_get_devices = AsyncMock(return_value=DEVICES)
        instance.voiceservice.async_get_calllist = AsyncMock(return_value=CALLLIST)
        instance.nemo.async_lucky_addr_address_lan = AsyncMock(
            return_value={"status": "1.2.3.4"}
        )
        instance.nemo.async_lucky_addr_address_data = AsyncMock(
            return_value={"status": "192.168.1.1"}
        )

        def _mock_get_mibs(*args, **kwargs):
            """Mock for async_get_MIBs to return different values based on first arg."""
            if args[0] == "data":
                return MIBS_DATA
            if args[0] == "lan":
                return MIBS_LAN
            if args[0] == "veip0":
                return MIBS_VEIP0
            return {}

        instance.nemo.async_get_MIBs = AsyncMock(side_effect=_mock_get_mibs)

        def _mock_get_net_dev_stats(*args, **kwargs):
            """Mock for async_get_net_dev_stats to return different values based on first arg."""
            if args[0] == "eth0":
                return NET_DEV_STATS_ETH0
            if args[0] == "veip0":
                return NET_DEV_STATS_VEIP0
            return {}

        instance.nemo.async_get_net_dev_stats = AsyncMock(
            side_effect=_mock_get_net_dev_stats
        )
        instance.nemo.async_get_dsl0_line_stats = AsyncMock(
            return_value=DSL0_LINE_STATS
        )
        instance.sfp.async_get = AsyncMock(return_value=SFP)

        def _mock_get_schedule(*args, **kwargs):
            """Mock for async_get_schedule to return different values based on first arg."""
            return {}

        instance.schedule.async_get_schedule = AsyncMock(side_effect=_mock_get_schedule)

        instance.schedule.async_get_scheduletypes = AsyncMock(
            return_value=SCHEDULETYPES
        )
        instance.dhcp.async_get_dhcp_pool = AsyncMock(return_value=DHCP_POOL)
        # instance.dhcp.async_get_dhcp_stats = AsyncMock(return_value=INFO)
        instance.dhcp.async_get_dhcp6_status = AsyncMock(
            return_value={"status": "Enabled"}
        )
        instance.dyndns.async_get_hosts = AsyncMock(return_value={"status": []})
        instance.dyndns.async_get_services = AsyncMock(
            return_value={
                "status": ["dyndns", "No-IP", "ChangeIP", "OVH-dynhost", "GnuDIP"]
            }
        )
        instance.dyndns.async_get_global_enable = AsyncMock(
            return_value={"status": True}
        )
        # instance.event.async_get_events = AsyncMock(return_value=INFO)  # take 10s
        instance.userinterface.async_get_language = AsyncMock(return_value=LANGUAGE)
        instance.userinterface.async_get_state = AsyncMock(
            return_value={"status": "connected"}
        )
        instance.upnpigd.async_get = AsyncMock(return_value=UPNPNGID)
        # instance.homelan.async_get_results = AsyncMock(return_value=INFO)  # take 5s
        # instance.homelan.async_get_devices_results = AsyncMock(return_value=INFO)  # take 13s
        instance.homelan.async_get_maxnumber_records = AsyncMock(
            return_value={"status": 8680}
        )
        instance.homelan.async_get_reading_interval = AsyncMock(
            return_value={"status": 30}
        )
        instance.homelan.async_get_devices_reading_interval = AsyncMock(
            return_value={"status": 30}
        )
        instance.homelan.async_get_devices_status = AsyncMock(
            return_value={"status": True}
        )
        instance.screen.async_get_show_wifi_password = AsyncMock(
            return_value={"status": True}
        )
        instance.pnp.async_get = AsyncMock(return_value=PNP)
        instance.iotservice.async_get_status = AsyncMock(return_value=IOT_STATUS)
        instance.time.async_get_time = AsyncMock(return_value=TIME)
        instance.time.async_get_utctime = AsyncMock(return_value=UTCTIME)
        instance.time.async_get_status = AsyncMock(return_value=TIME_STATUS)
        instance.time.async_get_ntp = AsyncMock(return_value=NTP)
        instance.time.async_get_localtime_zonename = AsyncMock(
            return_value=LOCALTIME_ZONE
        )
        instance.nmc.async_get = AsyncMock(return_value=NMC_GET)
        instance.nmc.async_get_wifi = AsyncMock(return_value=WIFI)
        instance.nmc.async_get_guest_wifi = AsyncMock(return_value=GUEST_WIFI)
        instance.nmc.async_get_wifi_stats = AsyncMock(return_value=WIFI_STATS)
        instance.nmc.async_get_lan_ip = AsyncMock(return_value=LAN_IP)
        instance.nmc.async_get_wanmodelist = AsyncMock(
            return_value={"status": "Ethernet_PPP;Ethernet_DHCP;GPON_DHCP;GPON_PPP"}
        )
        instance.nmc.async_get_wan_status = AsyncMock(return_value=WAN_STATUS)
        instance.nmc.async_update_versioninfo = AsyncMock(return_value={"status": True})
        instance.nmc.async_get_network = AsyncMock(return_value=NMC_NETWORK)
        instance.nmc.async_get_iptv_status = AsyncMock(return_value=NMC_IPTV)
        instance.nmc.async_get_iptv_config = AsyncMock(return_value=NMC_IPTV_CONFIG)
        instance.nmc.async_get_iptv_multi_screens = AsyncMock(
            return_value=NMC_IPTV_MULTI_SCREENS
        )
        instance.nmc.async_autodetect = AsyncMock(return_value=NMC_AUTODETECT)
        instance.nmc.async_get_wan_status = AsyncMock(return_value=WAN_STATUS)
        instance.nmc.async_get_remote_access = AsyncMock(return_value=INFO)
        instance.nmc.async_reboot = AsyncMock()
        instance.nmc.async_ring = AsyncMock()
        instance.usermanagement.async_get_users = AsyncMock(return_value=USERS)
        instance.usermanagement.async_get_groups = AsyncMock(return_value=GROUPS)
        instance.remoteaccess.async_get = AsyncMock(return_value=REMOTE_ACCESS)
        instance.orangeremoteaccess.async_get = AsyncMock(
            return_value=ORANGE_REMOTE_ACCESS
        )
        instance.speedtest.async_get_wan_results = AsyncMock(
            return_value=SPEEDTEST_INFOS
        )
        instance.sgcomci.async_get_optical = AsyncMock(return_value={})  # Livebox 5656
        instance.close = AsyncMock()
        yield instance


@pytest.fixture(name="config_entry")
def get_config_entry(hass: HomeAssistant) -> ConfigEntry:
    """Create and register mock config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=MOCK_USER_INPUT,
        unique_id="1",
        options={},
        entry_id="123456",
    )
    config_entry.add_to_hass(hass)
    return config_entry
