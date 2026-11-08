from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.service_info.ssdp import (
    ATTR_UPNP_FRIENDLY_NAME,
    ATTR_UPNP_SERIAL,
    SsdpServiceInfo,
)

from custom_components.livebox.const import CONF_USE_TLS, CONF_VERIFY_TLS

MOCK_USER_INPUT = {
    CONF_USERNAME: "192.168.1.1",
    CONF_PASSWORD: "mock_password",
    CONF_HOST: "192.168.1.1",
    CONF_PORT: 80,
    CONF_USE_TLS: False,
    CONF_VERIFY_TLS: False,
}


MOCK_SSDP_INFO = SsdpServiceInfo(
    ssdp_usn="mock_usn",
    ssdp_st="urn:schemas-upnp-org:device:InternetGatewayDevice:2",
    ssdp_location="http://192.168.1.1:49152/gatedesc.xml",
    upnp={
        ATTR_UPNP_FRIENDLY_NAME: "Orange Livebox",
        ATTR_UPNP_SERIAL: "012345678901234",
    },
)

# Raw `NMC.Reboot.Reboot:get` / `NMC.Reboot:get` replies, as returned by a
# Funbox 6. aiosysbus exposes no getter for them, so the coordinator reads them
# through `_auth.post` and the router mock answers from here.
MOCK_REBOOT_LOG = {
    "NMC.Reboot.Reboot": {
        "status": {
            "133": {
                "BootDate": "2026-09-06T12:50:00Z",
                "BootReason": "NMC",
                "ShutdownDate": "2026-09-16T01:07:24Z",
                "ShutdownReason": "TR069 reboot",
            },
            "134": {
                "BootDate": "2026-09-16T01:08:18Z",
                "BootReason": "NMC",
                "ShutdownDate": "0001-01-01T00:00:00Z",
                "ShutdownReason": "",
            },
        }
    },
    "NMC.Reboot": {
        "status": {
            "BootCounter": 134,
            "WatchdogRebootCounter": 3,
            "RebootSinceLastUpgrade": 85,
        }
    },
}
