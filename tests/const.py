from ipaddress import ip_address

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.service_info.zeroconf import (
    ATTR_PROPERTIES_ID,
    ZeroconfServiceInfo,
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
