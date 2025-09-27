"""Constants for the Livebox component."""

DOMAIN = "livebox"
COORDINATOR = "coordinator"
UNSUB_LISTENER = "unsubscribe_listener"
LIVEBOX_API = "api"
PLATFORMS = ["sensor", "binary_sensor", "switch", "button", "device_tracker"]

TEMPLATE_SENSOR = "Orange Livebox"

DEFAULT_USERNAME = "admin"
DEFAULT_HOST = "192.168.1.1"
DEFAULT_PORT = 80

CALLID = "callId"
CONF_USE_TLS = "use_tls"
CONF_VERIFY_TLS = "verify_tls"
CONF_LAN_TRACKING = "lan_tracking"
CONF_WIFI_TRACKING = "wifi_tracking"
DEFAULT_LAN_TRACKING = False
DEFAULT_WIFI_TRACKING = True

CONF_TRACKING_TIMEOUT = "timeout_tracking"
DEFAULT_TRACKING_TIMEOUT = 300

CONF_DISPLAY_DEVICES = "device_tracker_mode"
DEFAULT_DISPLAY_DEVICES = "Active"

UPLOAD_ICON = "mdi:upload-network"
DOWNLOAD_ICON = "mdi:download-network"
MISSED_ICON = "mdi:phone-alert"
RESTART_ICON = "mdi:restart-alert"
RING_ICON = "mdi:phone-classic"
GUESTWIFI_ICON = "mdi:wifi-lock-open"
DEVICE_WANACCESS_ICON = "mdi:wan"
RA_ICON = "mdi:remote-desktop"
DDNS_ICON = "mdi:dns"
PHONE_ICON = "mdi:card-account-phone-outline"
CLEARCALLS_ICON = "mdi:close-circle-multiple-outline"
