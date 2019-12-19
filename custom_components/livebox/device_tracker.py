"""Support for the Livebox platform."""
import logging

from homeassistant.components.device_tracker import SOURCE_TYPE_ROUTER
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import DATA_LIVEBOX, DOMAIN, ID_BOX, TRACK_ENTITIES, UNSUB_DEVICES

TRACKER_UPDATE = "{}_tracker_update".format(DOMAIN)
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up device tracker from config entry."""

    @callback
    def _receive_data(bridge_id, bridge, name, unique_id):
        """Receive set location."""
        if unique_id in hass.data[DOMAIN][TRACK_ENTITIES]:
            return
        hass.data[DOMAIN][TRACK_ENTITIES].add(device)
        async_add_entities(
            [LiveboxDeviceScannerEntity(bridge_id, bridge, name, unique_id)]
        )

    hass.data[DOMAIN][UNSUB_DEVICES][config_entry.entry_id] = async_dispatcher_connect(
        hass, TRACKER_UPDATE, _receive_data
    )

    bridge_id = hass.data[DOMAIN][ID_BOX]
    bridge = hass.data[DOMAIN][DATA_LIVEBOX]

    device_trackers = await bridge.async_get_devices()
    entities = []
    for device in device_trackers:
        if "IPAddress" in device:
            name = device["Name"]
            unique_id = device["PhysAddress"]
            hass.data[DOMAIN][TRACK_ENTITIES].add(unique_id)
            entity = LiveboxDeviceScannerEntity(bridge_id, bridge, name, unique_id)
            entities.append(entity)
    async_add_entities(entities, update_before_add=True)


class LiveboxDeviceScannerEntity(ScannerEntity):
    """Represent a tracked device."""

    def __init__(self, bridge_id, session, name, unique_id):
        """Initialize the device tracker."""
        self._bridge_id = id
        self._session = session
        self._name = name
        self._unique_id = unique_id
        self._connected = False
        self._unsubs = []

    @property
    def name(self):
        """Return Entity's default name."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def device_info(self):
        """Return the device info."""

        return {
            "name": self.name,
            "identifiers": {(DOMAIN, self.unique_id)},
            "via_device": (DOMAIN, self._bridge_id),
        }

    async def async_added_to_hass(self):
        """Register state update callback."""
        await super().async_added_to_hass()
        self._unsubs = async_dispatcher_connect(
            self.hass, TRACKER_UPDATE, self._async_receive_data
        )

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect entity object when removed."""
        await super().async_will_remove_from_hass()
        self._unsubs()

    async def async_update(self):
        """Handle polling."""
        if await self._update_entity():
            self._connected = True
        else:
            self._connected = False

    async def _update_entity(self):
        """Update entity."""
        return await self._session.async_get_device(self._unique_id)

    @property
    def is_connected(self):
        """Return true if the device is connected to the network."""
        return self._connected

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SOURCE_TYPE_ROUTER

    @callback
    def _async_receive_data(self, bridge_id, session, name, unique_id):
        """Mark the device as seen."""
        if name != self.name:
            return
        if self.async_update():
            self.async_write_ha_state()
