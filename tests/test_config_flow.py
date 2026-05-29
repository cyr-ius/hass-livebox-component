"""Test the livebox config flow."""

from unittest.mock import AsyncMock, patch

import pytest
from aiosysbus.exceptions import (
    AiosysbusException,
    AuthenticationFailed,
    HttpRequestFailed,
)
from homeassistant import config_entries, setup
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.livebox.const import DOMAIN

from .const import MOCK_USER_INPUT


@pytest.fixture(autouse=True)
def mock_setup_entry():
    """Override async_setup_entry."""
    with patch("custom_components.livebox.async_setup_entry", return_value=True):
        yield


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_form_success(
    hass: HomeAssistant,
    AIOSysbus: AsyncMock,
) -> None:
    """Test a successful setup flow."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch("custom_components.livebox.config_flow.AIOSysbus") as mock_livebox:
        # Simulate a successful connection and info retrieval
        mock_livebox.return_value = AIOSysbus

        # Start the config flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert not result.get("errors")

        # Simulate user submitting the form
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_USER_INPUT,
        )
        await hass.async_block_till_done()

        # Assert the flow finished and created an entry
        assert result2["type"] == FlowResultType.CREATE_ENTRY
        assert result2["title"] == "Livebox (012345678901234)"  # From INFO fixture
        assert result2["data"] == MOCK_USER_INPUT
        assert result2["result"].unique_id == "012345678901234"  # From INFO fixture


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_form_cannot_connect(hass: HomeAssistant, AIOSysbus: AsyncMock) -> None:
    """Test the flow handles connection errors."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch("custom_components.livebox.config_flow.AIOSysbus") as mock_livebox:
        # Simulate a successful connection and info retrieval
        mock_livebox.return_value = AIOSysbus
        mock_livebox.return_value.async_connect.side_effect = HttpRequestFailed(
            "Connection failed"
        )

        # Start the flow and submit data
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_USER_INPUT,
        )

        # Assert the form is shown again with a connection error
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_form_invalid_auth(hass: HomeAssistant, AIOSysbus: AsyncMock) -> None:
    """Test the flow handles invalid authentication."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch("custom_components.livebox.config_flow.AIOSysbus") as mock_livebox:
        # Simulate an authentication error
        mock_livebox.return_value = AIOSysbus
        mock_livebox.return_value.async_connect.side_effect = AuthenticationFailed(
            "Login error"
        )

        # Start the flow and submit data
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_USER_INPUT,
        )

        # Assert the form is shown again with an auth error
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "login_incorrect"}


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_form_unknown(hass: HomeAssistant, AIOSysbus: AsyncMock) -> None:
    """Test the flow handles invalid authentication."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch("custom_components.livebox.config_flow.AIOSysbus") as mock_livebox:
        # Simulate an authentication error
        mock_livebox.return_value = AIOSysbus
        mock_livebox.return_value.async_connect.side_effect = AiosysbusException(
            "Unknown error"
        )

        # Start the flow and submit data
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_USER_INPUT,
        )

        # Assert the form is shown again with an auth error
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_options_flow_active(hass: HomeAssistant, AIOSysbus: AsyncMock) -> None:
    """Test options flow accepts 'Active' as display_devices value."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.livebox.const import (
        CONF_DISPLAY_DEVICES,
        CONF_LAN_TRACKING,
        CONF_TRACKING_TIMEOUT,
        CONF_WIFI_TRACKING,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_USER_INPUT,
        options={
            CONF_WIFI_TRACKING: True,
            CONF_LAN_TRACKING: False,
            CONF_TRACKING_TIMEOUT: 300,
            CONF_DISPLAY_DEVICES: "Active",
        },
        unique_id="options-test-1234",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_WIFI_TRACKING: True,
            CONF_LAN_TRACKING: False,
            CONF_TRACKING_TIMEOUT: 300,
            CONF_DISPLAY_DEVICES: "Active",
        },
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_DISPLAY_DEVICES] == "Active"


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_form_already_configured(
    hass: HomeAssistant, AIOSysbus: AsyncMock
) -> None:
    """Test the flow aborts if the device is already configured."""
    # Create a mock entry to simulate existing configuration
    MockConfigEntry(
        domain=DOMAIN, unique_id="012345678901234", data=MOCK_USER_INPUT
    ).add_to_hass(hass)

    with patch("custom_components.livebox.config_flow.AIOSysbus") as mock_livebox:
        # Simulate a successful connection and info retrieval
        mock_livebox.return_value = AIOSysbus

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Simulate user submitting the form
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_USER_INPUT,
        )
        await hass.async_block_till_done()

        # Assert the flow is aborted
        assert result2["type"] == FlowResultType.ABORT
        assert result2["reason"] == "already_configured"
