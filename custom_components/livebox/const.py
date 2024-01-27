"""Constants for the Livebox component."""
DOMAIN = "livebox"
COORDINATOR = "coordinator"
UNSUB_LISTENER = "unsubscribe_listener"
LIVEBOX_API = "api"
PLATFORMS = ["sensor", "binary_sensor", "device_tracker", "switch", "button"]

TEMPLATE_SENSOR = "Orange Livebox"

DEFAULT_USERNAME = "admin"
DEFAULT_HOST = "192.168.1.1"
DEFAULT_PORT = 80

CALLID = "callId"
CONF_USE_TLS = "use_tls"
CONF_LAN_TRACKING = "lan_tracking"
DEFAULT_LAN_TRACKING = False

CONF_TRACKING_TIMEOUT = "timeout_tracking"
DEFAULT_TRACKING_TIMEOUT = 300

UPLOAD_ICON = "mdi:upload-network"
DOWNLOAD_ICON = "mdi:download-network"
MISSED_ICON = "mdi:phone-alert"
RESTART_ICON = "mdi:restart-alert"
RING_ICON = "mdi:phone-classic"
GUESTWIFI_ICON = "mdi:wifi-lock-open"
DEVICE_WANACCESS_ICON = "mdi:wan"
