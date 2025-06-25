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

![GitHub release](https://img.shields.io/github/release/Cyr-ius/hass-livebox-component)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

## Configuration

The preferred way to setup the Orange Livebox platform is by enabling the discovery component.

Add Livebox module via HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cyr-ius&repository=hass-livebox-component&category=integration)

Add your device via the Integration menu

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=livebox)

### Initial setup

You must have set a password for your Livebox router web administration page.

The first time Home Assistant will connect to your Livebox, you will need to specify the password of livebox.

### Options configure

You can use the Configure button to change the following options:

- Wired tracking (default: **No**): I track wired equipment
- Wireless tracking (default: **Yes**): I track wireless equipment
- Timeout tracking (default: **300 seconds**) : Time before the device is considered disconnected (Some iOS devices tend to disconnect/reconnect to networks unexpectedly)
- Track devices (default: **Active**):

  - All: Displays all active or inactive devices

  - Active: Displays only active devices (that have an IP address)

### Supported routers

Only the routers with Livebox OS are supported:

- Livebox v3
- Livebox v4
- Livebox v5
- Livebox v6
- Livebox v7 (not tested)
- KPN Box 12 (Firmware: V12.C.23.04.36)
- Sagemcom f@st 5656

### Unsupported routers

Despite being labelled "Livebox", the following router models **cannot** be supported:

- Arcadyan PRV3399 ("Livebox Plus")

## Presence Detection

This platform offers presence detection by keeping track of the
devices connected to a [Livebox](http://www.orange.fr/) router.

Ability to disable this option by integration options

### Notes

Note that the Livebox waits for some time before marking a device as inactive, meaning that there will be a small delay (1 or 2 minutes) between the time you disconnect a device and the time it will appear as "away" in Home Assistant.

You should take this into account when specifying the `consider_home` parameter.
On the contrary, the Livebox immediately reports devices newly connected, so they should appear as "home" almost instantly, as soon as Home Assistant refreshes the devices states.

## Sensor

This platform offers you sensors to monitor a Livebox router. The monitored conditions are instant upload and download rates in Mb/s.
