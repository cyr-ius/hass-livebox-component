"""Collect datas information from livebox."""


class BridgeData:
    """Simplification of API calls."""

    def __init__(self, session, config_entry):
        """Init parameters."""
        self._entry = config_entry
        self._session = session
        self._device = None
        self._devices = None

    async def async_get_devices(self):
        """Get all devices."""
        parameters = {
            "parameters": {
                "expression": {
                    "wifi": 'wifi and .IPAddress!="" and .PhysAddress!=""',
                    "eth": 'eth and .IPAddress!="" and .PhysAddress!="" and .DeviceType!=""',
                }
            }
        }
        devices = await self._session.system.get_devices(parameters)
        self._devices = devices.get("status", {}).get("wifi", {})
        device_eth = devices.get("status", {}).get("eth", {})
        if self._entry.options.get("lan_tracking", False):
            self._devices = self._devices + device_eth
        return self._devices

    async def async_get_device(self, unique_id):
        """Get device."""
        parameters = {
            "parameters": {
                "expression": {
                    "wifi": f'wifi and .PhysAddress=="{unique_id}"',
                    "eth": f'eth and .PhysAddress=="{unique_id }"',
                }
            }
        }
        self._device = (await self._session.system.get_devices(parameters)).get(
            "status"
        )
        if len(self._device.get("wifi", [])) == 1:
            return self._device["wifi"][0]["Active"] is True
        elif len(self._device.get("eth", [])) == 1:
            return self._device["eth"][0]["Active"] is True
        return False

    async def async_get_infos(self):
        """Get router infos."""
        infos = await self._session.system.get_deviceinfo()
        return infos.get("status", {})

    async def async_get_status(self):
        """Get status."""
        status = await self._session.system.get_WANStatus()
        return status.get("data", {})

    async def async_get_dsl_status(self):
        """Get dsl status."""
        parameters = {"parameters": {"mibs": "dsl", "flag": "", "traverse": "down"}}
        dsl_status = await self._session.connection.get_data_MIBS(parameters)
        return dsl_status.get("status", {}).get("dsl", {}).get("dsl0", {})
