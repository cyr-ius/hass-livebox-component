"""Support for the Livebox platform."""
from collections import namedtuple
import logging

from homeassistant.components.device_tracker import DeviceScanner

from . import DATA_LIVEBOX, DOMAIN

_LOGGER = logging.getLogger(__name__)



async def async_get_scanner(hass, config):
    """Validate the configuration and return a Livebox scanner."""
    bridge = hass.data[DOMAIN][DATA_LIVEBOX]
    scanner = LiveboxDeviceScanner(bridge)
    await scanner.async_connect()
    return scanner if scanner.success_init else None

Device = namedtuple("Device", ["id", "name", "ip"])

def _build_device(device_dict):
    return Device(
        device_dict["PhysAddress"],
        device_dict["Name"],
        device_dict["IPAddress"],
    )


class LiveboxDeviceScanner(DeviceScanner):
    """Represent a tracked device."""

    def __init__(self, bridge):
        """Initialize the scanner."""
        self.last_results = {}
        self.success_init = False
        self.bridge = bridge

    async def async_connect(self):
        """Initialize connection to the router."""
        # Test the router is accessible.
        data = await self.bridge.async_get_devices()
        self.success_init = data is not None

    async def async_scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        await self.async_update_info()
        return [device.id for device in self.last_results]

    async def async_get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        name = next(
            (result.name for result in self.last_results if result.id == device), None
        )
        return name

    async def async_get_extra_attributes(self,device):
        name = next(
            (result.name for result in self.last_results if result.id == device), None
        )
        _LOGGER.debug(device)
        _LOGGER.debug(name)
        
        return {"name": name}

    async def async_update_info(self):
        """Ensure the information from the Livebox router is up to date."""
        _LOGGER.debug("Checking Devices")
        hosts = await self.bridge.async_get_devices()
        last_results = [_build_device(device) for device in hosts if device["Active"]]
        _LOGGER.debug(last_results)        
        self.last_results = last_results
