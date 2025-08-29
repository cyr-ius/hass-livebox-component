from ipaddress import ip_address

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.service_info.zeroconf import (
    ATTR_PROPERTIES_ID,
    ZeroconfServiceInfo,
)
from pytest_homeassistant_custom_component.common import load_json_object_fixture

from custom_components.livebox.const import CONF_USE_TLS, CONF_VERIFY_TLS

CALLLIST = load_json_object_fixture("calllist.json")
DEVICES = load_json_object_fixture("devices.json")
DHCP_POOL = load_json_object_fixture("dhcp_pool.json")
DSL0 = load_json_object_fixture("dsl0_line_stats.json")
GROUPS = load_json_object_fixture("groups.json")
GROUPS = load_json_object_fixture("groups.json")
GUEST_WIFI = load_json_object_fixture("guest_wifi.json")
IOT_STATUS = load_json_object_fixture("iot_status.json")
LAN_IP = load_json_object_fixture("lan_ip.json")
LANGUAGE = load_json_object_fixture("language.json")
LOCALTIME_ZONE = load_json_object_fixture("localtime_zone.json")
MEM = load_json_object_fixture("dev_stats_veip0.json")
MIBS_DATA = load_json_object_fixture("MIBS_data.json")
MIBS_LAN = load_json_object_fixture("MIBS_lan.json")
MIBS_VEIP0 = load_json_object_fixture("MIBS_veip0.json")
NET_DEV_STATS_ETH0 = load_json_object_fixture("dev_stats_eth0.json")
NET_DEV_STATS_VEIP0 = load_json_object_fixture("dev_stats_veip0.json")
NMC_AUTODETECT = load_json_object_fixture("nmc_autodetect.json")
NMC_GET = load_json_object_fixture("nmc_get.json")
NMC_GET = load_json_object_fixture("nmc_get.json")
NMC_IPTV = load_json_object_fixture("nmc_iptv_status.json")
NMC_IPTV_CONFIG = load_json_object_fixture("nmc_iptv_config.json")
NMC_IPTV_MULTI_SCREENS = load_json_object_fixture("nmc_iptv_multi_screens.json")
NMC_NETWORK = load_json_object_fixture("nmc_network.json")
NTP = load_json_object_fixture("ntp.json")
ORANGE_REMOTE_ACCESS = load_json_object_fixture("orange_remote_access.json")
ORANGE_REMOTE_ACCESS = load_json_object_fixture("orange_remote_access.json")
PNP = load_json_object_fixture("pnp.json")
REMOTE_ACCESS = load_json_object_fixture("remote_access.json")
REMOTE_ACCESS = load_json_object_fixture("remote_access.json")
SCHEDULETYPES = load_json_object_fixture("schedule_types.json")
SFP = load_json_object_fixture("sfp.json")
SPEEDTEST_INFOS = load_json_object_fixture("speedtest_wan_result.json")
TIME = load_json_object_fixture("time.json")
TIME_STATUS = load_json_object_fixture("time_status.json")
UPNPNGID = load_json_object_fixture("upnpigd.json")
USERS = load_json_object_fixture("users.json")
USERS = load_json_object_fixture("users.json")
UTCTIME = load_json_object_fixture("utctime.json")
WAN_IP_STATS = load_json_object_fixture("wan_ip_stats.json")
WAN_STATUS = load_json_object_fixture("wan_status.json")
WIFI = load_json_object_fixture("wifi.json")
WIFI_STATS = load_json_object_fixture("wifi_stats.json")
DSL0_LINE_STATS = load_json_object_fixture("dsl0_line_stats.json")


MOCK_USER_INPUT = {
    CONF_USERNAME: "192.168.1.1",
    CONF_PASSWORD: "mock_password",
    CONF_HOST: "192.168.1.1",
    CONF_PORT: 80,
    CONF_USE_TLS: False,
    CONF_VERIFY_TLS: False,
}


MOCK_DISCOVERY_INFO = ZeroconfServiceInfo(
    ip_address=ip_address("192.168.1.1"),
    ip_addresses=[ip_address("192.168.1.1")],
    hostname="mock_hostname",
    name="_tcp.local.",
    port=None,
    properties={
        ATTR_PROPERTIES_ID: "00:00:00:00:00:00",
    },
    type="mock_type",
)
