"""Test the livebox config flow."""

from unittest.mock import AsyncMock, patch

import pytest
from aiosysbus.exceptions import (
    AiosysbusException,
    AuthenticationFailed,
    HttpRequestFailed,
    InsufficientPermissionsError,
    RetrieveFailed,
)
from homeassistant import config_entries, setup
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.livebox.const import (
    CONF_DISPLAY_DEVICES,
    DEFAULT_DISPLAY_DEVICES,
    DOMAIN,
)

from .const import MOCK_SSDP_INFO, MOCK_USER_INPUT


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
        product_class = AIOSysbus.api_raw["DeviceInfo.async_get_deviceinfo"]["status"][
            "ProductClass"
        ]
        assert result2["title"] == f"{product_class} (012345678901234)"
        assert result2["data"] == MOCK_USER_INPUT
        assert result2["result"].unique_id == "012345678901234"  # From INFO fixture

    # The validation session is released, the integration opens its own one.
    AIOSysbus.async_logout.assert_awaited_once()


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
@pytest.mark.parametrize(
    ("method", "side_effect", "error"),
    [
        ("async_connect", HttpRequestFailed("Connection failed"), "cannot_connect"),
        ("async_connect", RetrieveFailed("No response"), "cannot_connect"),
        ("async_connect", AuthenticationFailed("Login error"), "login_incorrect"),
        (
            "async_get_permissions",
            InsufficientPermissionsError("Permission denied"),
            "insufficient_permission",
        ),
        ("async_connect", AiosysbusException("Unknown error"), "unknown"),
    ],
)
async def test_form_errors_recover(
    hass: HomeAssistant,
    AIOSysbus: AsyncMock,
    method: str,
    side_effect: Exception,
    error: str,
) -> None:
    """An error shows the form again and the flow completes once it is fixed."""
    getattr(AIOSysbus, method).side_effect = side_effect

    with patch("custom_components.livebox.config_flow.AIOSysbus") as mock_livebox:
        mock_livebox.return_value = AIOSysbus
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_USER_INPUT
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": error}

        getattr(AIOSysbus, method).side_effect = None
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_USER_INPUT
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "012345678901234"


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_form_without_serial_number(
    hass: HomeAssistant, AIOSysbus: AsyncMock
) -> None:
    """A Livebox answering without serial number cannot be configured."""
    infos = AIOSysbus.api_raw["DeviceInfo.async_get_deviceinfo"]["status"]
    serial = infos.pop("SerialNumber")

    with patch("custom_components.livebox.config_flow.AIOSysbus") as mock_livebox:
        mock_livebox.return_value = AIOSysbus
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_USER_INPUT,
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}

        infos["SerialNumber"] = serial
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_USER_INPUT
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_ssdp_discovery(hass: HomeAssistant, AIOSysbus: AsyncMock) -> None:
    """A Livebox discovered over SSDP is set up through the user form."""
    with patch("custom_components.livebox.config_flow.AIOSysbus") as mock_livebox:
        mock_livebox.return_value = AIOSysbus
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_SSDP},
            data=MOCK_SSDP_INFO,
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_USER_INPUT
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "012345678901234"


async def test_ssdp_discovery_already_configured(hass: HomeAssistant) -> None:
    """A Livebox already configured is not discovered again."""
    MockConfigEntry(
        domain=DOMAIN, unique_id="012345678901234", data=MOCK_USER_INPUT
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data=MOCK_SSDP_INFO,
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


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


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_reconfigure_updates_entry(
    hass: HomeAssistant,
    AIOSysbus: AsyncMock,
) -> None:
    """Test reconfiguring an existing entry updates its data."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Livebox (012345678901234)",
        unique_id="012345678901234",
        data=MOCK_USER_INPUT,
    )
    entry.add_to_hass(hass)

    new_input = {
        **MOCK_USER_INPUT,
        "password": "updated_password",
    }

    with (
        patch("custom_components.livebox.config_flow.AIOSysbus") as mock_livebox,
        patch.object(hass.config_entries, "async_schedule_reload") as mock_reload,
    ):
        mock_livebox.return_value = AIOSysbus

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reconfigure"
        assert not result.get("errors")

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            new_input,
        )
        await hass.async_block_till_done()

        assert result2["type"] == FlowResultType.ABORT
        assert result2["reason"] == "reconfigure_successful"
        assert entry.data == new_input
        mock_reload.assert_called_once_with(entry.entry_id)


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_form_logout_error(hass: HomeAssistant, AIOSysbus: AsyncMock) -> None:
    """A failed release of the validation session does not fail the flow."""
    AIOSysbus.async_logout.side_effect = HttpRequestFailed("Connection failed")

    with patch("custom_components.livebox.config_flow.AIOSysbus") as mock_livebox:
        mock_livebox.return_value = AIOSysbus
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_USER_INPUT,
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize("stored", [None, "Active"])
async def test_options_flow_defaults_are_valid(
    hass: HomeAssistant, stored: str | None
) -> None:
    """The options form accepts its defaults, including the legacy value."""
    options = {} if stored is None else {CONF_DISPLAY_DEVICES: stored}
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT, options=options)
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DISPLAY_DEVICES] == DEFAULT_DISPLAY_DEVICES


@pytest.fixture
def reauth_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a configured Livebox whose password was changed."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Livebox 7 (012345678901234)",
        unique_id="012345678901234",
        data=MOCK_USER_INPUT,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_reauth(
    hass: HomeAssistant, AIOSysbus: AsyncMock, reauth_entry: MockConfigEntry
) -> None:
    """New credentials are stored, a rejected password can be typed again."""
    AIOSysbus.async_connect.side_effect = AuthenticationFailed("Login error")

    with (
        patch("custom_components.livebox.config_flow.AIOSysbus") as mock_livebox,
        patch.object(hass.config_entries, "async_schedule_reload") as mock_reload,
    ):
        mock_livebox.return_value = AIOSysbus
        result = await reauth_entry.start_reauth_flow(hass)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"
        assert result["description_placeholders"] == {"name": reauth_entry.title}

        credentials = {"username": "admin", "password": "new_password"}
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], credentials
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "login_incorrect"}

        AIOSysbus.async_connect.side_effect = None
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], credentials
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert reauth_entry.data == {**MOCK_USER_INPUT, **credentials}
    mock_reload.assert_called_once_with(reauth_entry.entry_id)


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_reauth_other_livebox(
    hass: HomeAssistant, AIOSysbus: AsyncMock, reauth_entry: MockConfigEntry
) -> None:
    """Credentials of another Livebox do not replace those of the entry."""
    AIOSysbus.api_raw["DeviceInfo.async_get_deviceinfo"]["status"]["SerialNumber"] = (
        "999999999999999"
    )

    with patch("custom_components.livebox.config_flow.AIOSysbus") as mock_livebox:
        mock_livebox.return_value = AIOSysbus
        result = await reauth_entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"username": "admin", "password": "new_password"}
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
    assert reauth_entry.data == MOCK_USER_INPUT


async def test_ssdp_discovery_updates_host(hass: HomeAssistant) -> None:
    """A configured Livebox found at a new address gets its host updated."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="012345678901234",
        data={**MOCK_USER_INPUT, CONF_HOST: "192.168.0.254"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data=MOCK_SSDP_INFO,
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == "192.168.1.1"
