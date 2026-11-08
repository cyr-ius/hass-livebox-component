# Orange Livebox Router

This a _custom component_ for [Home Assistant](https://www.home-assistant.io/).
The `livebox` integration allows you to observe and control [Livebox router](http://www.orange.fr/).

There is currently support for the following device types within Home Assistant:

- Sensor with traffic metrics
- Binary Sensor with wan status , public ip , private ip
- Device tracker for connected devices (via option add wired devices)
- Switch for enable/disable Wireless and Guest Wifi
- Press button to restart box
- Press button to ring phone
- Press button to clear calls

![GitHub release](https://img.shields.io/github/release/Cyr-ius/hass-livebox-component)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
![downloads](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.livebox.total)

## Development

This repository uses [`uv`](https://docs.astral.sh/uv/) for local development.

```bash
uv sync --group dev
uv run pytest
uv run pyrefly check custom_components tests
uv run pre-commit run --all-files
```

## Configuration

The preferred way to setup the Orange Livebox platform is by enabling the discovery component.

Add Livebox module via HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cyr-ius&repository=hass-livebox-component&category=integration)

Add your device via the Integration menu

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=livebox)

### Initial setup

You must have set a password for your Livebox router web administration page.

The Livebox is discovered automatically (SSDP). Otherwise add it from **Settings** > **Devices & services** > **Add integration** > **Orange Livebox**, then fill in:

| Parameter              | Default       | Description                                                                       |
| ---------------------- | ------------- | --------------------------------------------------------------------------------- |
| Host                   | `192.168.1.1` | IP address or hostname of the Livebox.                                            |
| Username               | `admin`       | Administrator account of the Livebox.                                             |
| Password               |               | Administrator password, printed on the Livebox label unless you changed it.       |
| Port                   | `80`          | Port of the Livebox web interface (`443` over HTTPS).                             |
| Use TLS                | No            | Connect to the Livebox over HTTPS.                                                |
| Verify TLS certificate | Yes           | Check the certificate presented by the Livebox. Disable it for a self-signed one. |

These settings can be changed later with **Reconfigure** on the Livebox entry. When the Livebox rejects the password (it was changed on the router, for instance), Home Assistant asks for the new one.

### Options configure

You can use the Configure button to change the following options:

- Wired tracking (default: **No**): I track wired equipment
- Wireless tracking (default: **Yes**): I track wireless equipment
- Timeout tracking (default: **300 seconds**) : Time before the device is considered disconnected (Some iOS devices tend to disconnect/reconnect to networks unexpectedly)
- Devices to track (default: **Active devices only**):
  - All devices: active and inactive devices known by the Livebox
  - Active devices only: devices currently connected (that have an IP address)

### Supported routers

Only the routers with Livebox OS are supported:

- Livebox 3
- Livebox 4
- Livebox 5
- Livebox 6
- Livebox 7
- Livebox W7
- KPN Box 12 (Firmware: V12.C.23.04.36)
- Sagemcom f@st 5656
- Livebox Nautilus (Arcadyan)

### Unsupported routers

Despite being labelled "Livebox", the following router models **cannot** be supported:

- Arcadyan PRV3399 (["Livebox Plus"](https://ayuda.orange.es/dispositivos-y-routers/2381-router-livebox-plus))
- Arcadyan ERV33AX349B-LT (ARLTFIBRA6 or ["Livebox 6+"](https://ayuda.orange.es/dispositivos-y-routers/2755-router-livebox-6plus))
- ZTE ZTEGLB7xxxxxx (["Livebox 7 ZTE"](https://ayuda.orange.es/dispositivos-y-routers/3220-router-livebox-7))

## Supported functions

### Livebox

| Platform      | Entity                                                                 | Notes                                                                         |
| ------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Binary sensor | WAN status                                                             | WAN IP addresses, link type and wired / wireless client counts as attributes. |
| Binary sensor | Call missed                                                            | On while missed calls are in the call list (`missed_calls` attribute).        |
| Binary sensor | Remote access                                                          | Remote administration of the Livebox enabled.                                 |
| Binary sensor | Dynamic DNS (_service_)                                                | One per DynDNS host, on when the last update failed.                          |
| Sensor        | xDSL download / upload                                                 | xDSL lines only. Line attenuation, noise margin and power as attributes.      |
| Sensor        | Fiber power Rx / Tx, Fiber Rx / Tx                                     | Fiber gateways with an ONT only.                                              |
| Sensor        | _Interface_ rate Rx / Tx                                               | Current rate of each LAN interface.                                           |
| Sensor        | Callers                                                                | Number of calls in the call list.                                             |
| Sensor        | Wifi Rx / Tx, Ports forwarding, DHCP leases, Guest DHCP leases, Uptime | Disabled by default.                                                          |
| Sensor        | Last reboot reason                                                     | Not available on Livebox 3.                                                   |
| Switch        | Wifi, Guest Wifi                                                       | Turn the Wi-Fi networks on or off.                                            |
| Button        | Livebox restart, Ring your phone, Clear calls                          |                                                                               |
| Calendar      | Call log                                                               | Incoming, outgoing and missed calls.                                          |

### Connected devices

| Platform       | Entity                                                                     | Notes                                                        |
| -------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Device tracker | _Device name_                                                              | Wireless devices by default, wired ones through the options. |
| Switch         | WAN access                                                                 | Block or allow the Internet access of the device.            |
| Sensor         | Downlink / uplink rate, Tx / Rx bytes, Signal strength, Signal noise ratio | Wireless devices only, disabled by default.                  |

## Data updates

The integration polls the Livebox on the local network every minute. The mesh topology (which repeater a device is connected to) is read every 5 minutes, and once a day when no Wi-Fi repeater is found.

Devices connected for the first time are added automatically, with their entities. Devices that left the network are kept: delete them from their device page when you no longer need them (the Livebox itself cannot be deleted this way).

## Presence detection

Device trackers report whether a device is connected to the Livebox. The Livebox waits for some time before marking a device as inactive, so a device appears as "away" 1 or 2 minutes after it left, plus the **Away timeout** option. Newly connected devices are reported immediately and appear as "home" at the next refresh.

## Use cases

- Know who is at home from the phones connected to the Wi-Fi.
- Turn the guest Wi-Fi on when guests arrive, off at night.
- Block the Internet access of the children devices at bedtime.
- Get notified of a missed call or of a WAN outage.
- Follow the fiber optical power or the xDSL line quality over time.

## Examples

Turn the guest Wi-Fi off every night:

```yaml
automation:
  - alias: "Guest Wi-Fi off at night"
    triggers:
      - trigger: time
        at: "23:00:00"
    actions:
      - action: switch.turn_off
        target:
          entity_id: switch.livebox_7_guest_wifi
```

Notify a missed call, then clear the call list:

```yaml
automation:
  - alias: "Missed call"
    triggers:
      - trigger: state
        entity_id: binary_sensor.livebox_7_call_missed
        to: "on"
    actions:
      - action: notify.notify
        data:
          message: "Missed call on the Livebox"
      - action: livebox.remove_call_missed
```

Warn when the Internet connection drops for more than 5 minutes:

```yaml
automation:
  - alias: "Livebox WAN down"
    triggers:
      - trigger: state
        entity_id: binary_sensor.livebox_7_wan_status
        to: "off"
        for: "00:05:00"
    actions:
      - action: notify.notify
        data:
          message: "The Internet connection is down"
```

Entity IDs depend on the model of your Livebox (here a Livebox 7): check them in **Settings** > **Devices & services** > **Entities**.

## Known limitations

- The Livebox accepts a limited number of open sessions. The integration releases its session when it stops, but after a power loss the previous session stays open until the Livebox expires it.
- Wired devices are not tracked by default: enable **Wired tracking** in the options.
- xDSL sensors only exist on xDSL lines, fiber sensors only on gateways with an ONT.
- The counters of the Livebox are 32-bit: they roll over and restart from 0 when the Livebox reboots; Home Assistant statistics handle both.
- The call log calendar is kept in memory: it restarts empty when Home Assistant or the Livebox restarts.
- WAN access switches use the Livebox parental control schedules, a schedule set on the Livebox web interface overrides them.

## Troubleshooting

- **Unable to connect to the Livebox**: check the host and port, and that **Use TLS** matches the port (443 for HTTPS). With a self-signed certificate, disable **Verify TLS certificate**.
- **Invalid username or password**: use the `admin` account and the password of the Livebox web interface. When it changes, Home Assistant asks for the new one.
- **The account does not have enough permissions**: use the `admin` account.
- **Entities become unavailable from time to time**: the Livebox may reject new sessions when too many are open (web interface, mobile app). Close them or reboot the Livebox.
- **A device stays "home"**: lower the **Away timeout** option.

To report a problem, enable the debug logs from the Livebox entry menu (**Enable debug logging**), reproduce it, then attach the logs and the diagnostics (**Download diagnostics**) to an [issue](https://github.com/cyr-ius/hass-livebox-component/issues). Passwords, serial numbers and MAC addresses are removed from the diagnostics.

## Actions

### `livebox.remove_call_missed`

Removes missed calls from the call list of the Livebox.

| Field             | Required | Description                                                                                                     |
| ----------------- | -------- | --------------------------------------------------------------------------------------------------------------- |
| `callId`          | No       | ID of the call, shown in the `missed_calls` attribute of the _Call missed_ binary sensor. All calls if omitted. |
| `config_entry_id` | No       | Livebox whose call list is cleared. All configured Livebox if omitted.                                          |

```yaml
action: livebox.remove_call_missed
data:
  callId: "666"
```

## Removal

This integration follows the standard integration removal process; no extra step is required.

1. Go to **Settings** > **Devices & services** and select **Orange Livebox**.
2. Open the menu (⋮) of the Livebox entry and select **Delete**.
3. To remove the files as well, open **HACS**, select **Orange Livebox**, open its menu and select **Remove**, then restart Home Assistant.

The session opened on the Livebox is closed when the entry is deleted.
