"""Support for the Livebox platform."""
import logging
from datetime import datetime, timedelta

from homeassistant.components.device_tracker import SOURCE_TYPE_ROUTER
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CONF_TRACKING_TIMEOUT, COORDINATOR, DOMAIN, LIVEBOX_ID
from .coordinator import LiveboxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up device tracker from config entry."""
    datas = hass.data[DOMAIN][config_entry.entry_id]
    box_id = datas[LIVEBOX_ID]
    coordinator = datas[COORDINATOR]
    timeout = datas[CONF_TRACKING_TIMEOUT]

    device_trackers = coordinator.data["devices"]
    entities = [
        LiveboxDeviceScannerEntity(key, box_id, coordinator, timeout)
        for key, device in device_trackers.items()
        if "IPAddress" and "PhysAddress" in device
    ]
    async_add_entities(entities, True)


class LiveboxDeviceScannerEntity(
    CoordinatorEntity[LiveboxDataUpdateCoordinator], ScannerEntity
):
    """Represent a tracked device."""

    _attr_has_entity_name = True

    def __init__(self, key, bridge_id, coordinator, timeout):
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self.box_id = bridge_id
        self.key = key
        self._device = coordinator.data.get("devices", {}).get(key, {})
        self._timeout_tracking = timeout
        self._old_status = datetime.today()

        self._attr_name = self._device.get("Name")
        self._attr_unique_id = key 
        

    @property
    def is_connected(self):
        """Return true if the device is connected to the network."""
        status = (
            self.coordinator.data.get("devices", {})
            .get(self.unique_id, {})
            .get("Active")
        )
        if status is True:
            self._old_status = datetime.today() + timedelta(
                seconds=self._timeout_tracking
            )
        if status is False and self._old_status > datetime.today():
            _LOGGER.debug("%s will be disconnected at %s", self.name, self._old_status)
            return True

        return status

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SOURCE_TYPE_ROUTER

    @property
    def ip_address(self):
        """Return ip address."""
        device = self.coordinator.data["devices"].get(self.unique_id, {})
        return device.get("IPAddress")

    @property
    def mac_address(self):
        """Return mac address."""
        return self.key
# added LGO
    @property
    def link(self):
        return (
            self.coordinator.data.get("devices", {})
            .get(self.unique_id, {})
            .get("Interface")
        )  

    @property
    def icon(self):
        """Return icon."""    
        
        device = self.coordinator.data.get("devices", {}).get(self.unique_id, {}).get("DeviceType")   
        if  device in ["Computer", "Desktop iOS","Desktop Windows","Desktop Linux" ]:
            return "mdi:desktop-tower-monitor"    
        elif device in ["Laptop", "Laptop iOS", "Laptop Windows","Laptop Linux"]:
            return "mdi:laptop"
        elif device in ["Switch4", "Switch8","Switch"  ]:
            return "mdi:switch"
        elif device in ["Acces Point",   ]:
            return "mdi:access-point-network"
        elif device in ["TV","TVKey","Apple TV" ]:
            return "mdi:television"
        elif device == "HomePlug":
            return "mdi:network"    
        elif device ==  "Printer":
            return "mdi:printer"  
        elif device in ["Set-top Box TV UHD", "Set-top Box"]:
            return "mdi:dlna"          
        elif device in ["Mobile iOS", "Mobile" ,"Mobile Android"]:
            return "mdi:cellphone"    
        elif device in ["Table iOS", "Tablet" ,"Tablet Android"]:
            return "mdi:cellphone"   
        elif device in ["Game Console", ]:
            return "mdi:gamepad-square"   
        elif device in  ["Homepoint"]:
            return "mdi:home-automation"     
        else:           
            return "mdi:devices"                    

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "name": self.name,
            "identifiers": {(DOMAIN, self.unique_id)},
            "via_device": (DOMAIN, self.box_id),
        }

            
    @property
    def extra_state_attributes(self):
        """Return the device state attributes."""
        attrs = {}
    #added by LGO    
        attrs["scanner"] = "LiveboxDeviceScanner"
        attrs["is_online"] = self._device.get("Active")
        attrs["interface_name"] = self._device.get("InterfaceName")
        attrs["ip_address"] = self._device.get("IPAddress")

    #  connection ethernet wired or wifi      
        if self._device.get("InterfaceName") in ["eth1" ,"eth2","eth3", "eth4", "eth5" ] :   
            attrs["connection"] = "ethernet" 
            attrs["is_wireless"] = False
        else:    
            if self._device.get("InterfaceName") in ["eth6","wlan0"]  :   
                attrs["connection"] = "wifi" 
                attrs["band"] = self._device.get("OperatingFrequencyBand")
                attrs["signal_strength"] = self._device.get("SignalStrength")
                attrs["is_wireless"] = True
                # signal Quality
                if self._device.get("SignalStrength") < -90 : 
                    attrs["signal_quality"] ="very bad"
                elif self._device.get("SignalStrength") <= -80 and self._device.get("SignalStrength") > -90 : 
                    attrs["signal_quality"] =" bad"
                elif self._device.get("SignalStrength") <= -70 and self._device.get("SignalStrength") > -80 : 
                    attrs["signal_quality"] = "very low"
                elif self._device.get("SignalStrength") <= -67 and self._device.get("SignalStrength") > -70 : 
                    attrs["signal_quality"] = "low"
                elif self._device.get("SignalStrength") <= -60 and self._device.get("SignalStrength") > -67 : 
                    attrs["signal_quality"] = "good"
                elif self._device.get("SignalStrength") <= -50 and self._device.get("SignalStrength") > -60 : 
                    attrs["signal_quality"] = "very good"
                elif self._device.get("SignalStrength") <= -30 and self._device.get("SignalStrength") > -50 : 
                    attrs["signal_quality"] ="excellent"
            else:
                attrs["signal_quality"] ="unknown"  
        
        attrs["type"] = self._device.get("DeviceType")
        attrs["vendor"] = self._device.get("VendorClassID")
        attrs["manufacturer"] = self._device.get("Manufacturer")
        attrs["first_seen"] = self._device.get("FirstSeen")
        attrs["last_connection"] = self._device.get("LastConnection")
        attrs["last_changed"] = self._device.get("LastChanged")

        return attrs
