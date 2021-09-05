"""Constants for the Livebox component."""
DOMAIN = "livebox"
COORDINATOR = "coordinator"
UNSUB_LISTENER = "unsubscribe_listener"
LIVEBOX_ID = "id"
LIVEBOX_API = "api"
COMPONENTS = ["sensor", "binary_sensor", "device_tracker", "switch"]

TEMPLATE_SENSOR = "Orange Livebox"

DEFAULT_USERNAME = "admin"
DEFAULT_HOST = "192.168.1.1"
DEFAULT_PORT = 80

CALLID = "callId"

CONF_LAN_TRACKING = "lan_tracking"
DEFAULT_LAN_TRACKING = False

CONF_TRACKING_TIMEOUT = "timeout_tracking"
DEFAULT_TRACKING_TIMEOUT = 300
