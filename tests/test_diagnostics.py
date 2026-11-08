"""Tests for the Livebox diagnostics."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator


def _named(method: AsyncMock, name: str) -> AsyncMock:
    """Give a mocked API method the qualified name diagnostics key it by."""
    method.__qualname__ = name
    return method


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_config_entry_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Diagnostics dump the API responses with credentials redacted."""
    AIOSysbus.time.async_get_time = _named(
        AsyncMock(side_effect=RuntimeError("boom")), "Time.async_get_time"
    )
    AIOSysbus.nemo.async_lucky_addr_address = _named(
        AsyncMock(return_value={"status": "192.168.1.1"}),
        "NeMo.async_lucky_addr_address",
    )
    _named(AIOSysbus.deviceinfo.async_get_deviceinfo, "DeviceInfo.async_get_deviceinfo")
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await get_diagnostics_for_config_entry(hass, hass_client, config_entry)

    assert result["entry"]["data"]["password"] == "**REDACTED**"
    assert result["entry"]["data"]["host"] == "**REDACTED**"
    assert result["entry"]["data"]["port"] == config_entry.data["port"]
    assert result["data"]["infos"]["SerialNumber"] == "**REDACTED**"
    api_raw = result["api_raw"]
    assert api_raw["DeviceInfo.async_get_deviceinfo"]["status"]["ProductClass"]
    for interface in ("lan", "data"):
        lucky_address = api_raw[f"NeMo.async_lucky_addr_address::{interface}"]
        assert lucky_address["status"] == "**REDACTED**"
    assert api_raw["Time.async_get_time"] == "Exception: boom"
