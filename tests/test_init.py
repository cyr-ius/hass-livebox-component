"""Tests for the Livebox integration setup helpers and services."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.livebox.const import DOMAIN


async def test_remove_call_missed_targets_loaded_entries(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """The service clears the call list of loaded entries only."""
    clear = AIOSysbus.voiceservice.async_clear_calllist = AsyncMock()
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "remove_call_missed",
        {"callId": "1", "config_entry_id": config_entry.entry_id},
        blocking=True,
    )
    clear.assert_awaited_once_with({"callId": "1"})

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "remove_call_missed", {"config_entry_id": "unknown"}, blocking=True
        )

    # The service outlives the entry and no longer reaches its coordinator.
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    clear.reset_mock()
    await hass.services.async_call(DOMAIN, "remove_call_missed", {}, blocking=True)
    clear.assert_not_awaited()


@pytest.mark.usefixtures("AIOSysbus")
async def test_livebox_device_cannot_be_removed(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Client devices can be removed from the UI, the Livebox itself cannot."""
    assert await async_setup_component(hass, "config", {})
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    gateway = device_registry.async_get_device_by_identifier(
        (DOMAIN, "012345678901234"), config_entry.entry_id
    )
    assert gateway is not None
    client_device = next(
        device
        for device in dr.async_entries_for_config_entry(
            device_registry, config_entry.entry_id
        )
        if device.id != gateway.id
    )

    client = await hass_ws_client(hass)

    async def _remove(device_id: str) -> bool:
        await client.send_json_auto_id(
            {
                "type": "config/device_registry/remove_config_entry",
                "config_entry_id": config_entry.entry_id,
                "device_id": device_id,
            }
        )
        return (await client.receive_json())["success"]

    assert not await _remove(gateway.id)
    assert await _remove(client_device.id)
