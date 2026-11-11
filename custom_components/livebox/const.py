"""Constants for the Livebox component."""

DOMAIN = "livebox"
COORDINATOR = "coordinator"
UNSUB_LISTENER = "unsubscribe_listener"
LIVEBOX_API = "api"
PLATFORMS = [
    "sensor",
    "binary_sensor",
    "switch",
    "button",
    "device_tracker",
    "calendar",
]

TEMPLATE_SENSOR = "Orange Livebox"

DEFAULT_USERNAME = "admin"
DEFAULT_HOST = "192.168.1.1"
DEFAULT_PORT = 80

CALLID = "callId"
ATTR_CALL_ID = "call_id"
CONF_USE_TLS = "use_tls"
CONF_VERIFY_TLS = "verify_tls"
CONF_LAN_TRACKING = "lan_tracking"
CONF_WIFI_TRACKING = "wifi_tracking"
DEFAULT_LAN_TRACKING = False
DEFAULT_WIFI_TRACKING = True
CONF_WAN_ACCESS = "wan_access_switches"
DEFAULT_WAN_ACCESS = True

CONF_TRACKING_TIMEOUT = "timeout_tracking"
DEFAULT_TRACKING_TIMEOUT = 300

CONF_DISPLAY_DEVICES = "device_tracker_mode"
DISPLAY_DEVICES_ALL = "all"
DEFAULT_DISPLAY_DEVICES = "active_only"
