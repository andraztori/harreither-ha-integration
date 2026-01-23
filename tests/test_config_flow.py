"""Config flow tests for the Harreither Integration."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.harreither.api import (
    IntegrationBlueprintApiClientAuthenticationError,
    IntegrationBlueprintApiClientCommunicationError,
    IntegrationBlueprintApiClientError,
)
from custom_components.harreither.const import DOMAIN

from tests.common import MockConfigEntry

# Mock test data
TEST_HOST = "192.168.1.100"
TEST_USERNAME = "test_user"
TEST_PASSWORD = "test_password"
TEST_UNIQUE_ID = "test-user"  # slugified version of username


async def test_user_flow_success(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test successful config flow initiated by user."""
    with patch(
        "custom_components.harreither.config_flow.IntegrationBlueprintApiClient"
    ) as mock_client:
        mock_client.return_value.async_get_data = AsyncMock(return_value={})

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == TEST_USERNAME
        assert result["data"] == {
            CONF_HOST: TEST_HOST,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        }
        assert result["result"].unique_id == TEST_UNIQUE_ID
        assert len(mock_setup_entry.mock_calls) == 1


async def test_user_flow_connection_error(
    hass: HomeAssistant,
) -> None:
    """Test config flow with connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    # Simulate connection error
    with patch(
        "custom_components.harreither.config_flow.IntegrationBlueprintApiClient"
    ) as mock_client:
        mock_client.return_value.async_get_data = AsyncMock(
            side_effect=IntegrationBlueprintApiClientCommunicationError(
                "Connection error"
            )
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "connection"}


async def test_user_flow_invalid_auth(
    hass: HomeAssistant,
) -> None:
    """Test config flow with authentication error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    # Simulate authentication error
    with patch(
        "custom_components.harreither.config_flow.IntegrationBlueprintApiClient"
    ) as mock_client:
        mock_client.return_value.async_get_data = AsyncMock(
            side_effect=IntegrationBlueprintApiClientAuthenticationError(
                "Invalid credentials"
            )
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "auth"}


async def test_user_flow_unknown_error(
    hass: HomeAssistant,
) -> None:
    """Test config flow with unknown error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    # Simulate unknown error
    with patch(
        "custom_components.harreither.config_flow.IntegrationBlueprintApiClient"
    ) as mock_client:
        mock_client.return_value.async_get_data = AsyncMock(
            side_effect=IntegrationBlueprintApiClientError("Unknown error")
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "unknown"}


async def test_user_flow_duplicate_entry(
    hass: HomeAssistant,
) -> None:
    """Test config flow aborts when entry already exists."""
    # Create an existing entry with the same unique_id that will be generated
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: TEST_HOST,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
        unique_id=TEST_UNIQUE_ID,  # This matches what slugify(TEST_USERNAME) produces
        title=TEST_USERNAME,
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.harreither.config_flow.IntegrationBlueprintApiClient"
    ) as mock_client:
        mock_client.return_value.async_get_data = AsyncMock(return_value={})

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


# Note: Reauth flow tests are commented out as the component
# doesn't appear to implement reauth yet. Uncomment and adjust when reauth is added.
#
# async def test_reauth_flow_success(
#     hass: HomeAssistant,
#     mock_config_entry: MockConfigEntry,
#     mock_setup_entry: AsyncMock,
# ) -> None:
#     """Test successful reauthentication flow."""
#     with patch(
#         "custom_components.harreither.config_flow.IntegrationBlueprintApiClient"
#     ) as mock_client:
#         mock_client.return_value.async_get_data = AsyncMock(return_value={})
#
#         result = await mock_config_entry.start_reauth_flow(hass)
#
#         assert result["type"] is FlowResultType.FORM
#         assert result["step_id"] == "reauth_confirm"
#         assert result["errors"] == {}
#
#         result = await hass.config_entries.flow.async_configure(
#             result["flow_id"],
#             user_input={CONF_PASSWORD: "new_password"},
#         )
#
#         assert result["type"] is FlowResultType.ABORT
#         assert result["reason"] == "reauth_successful"
#         assert mock_config_entry.data[CONF_PASSWORD] == "new_password"
#
#
# async def test_reauth_flow_invalid_auth(
#     hass: HomeAssistant,
#     mock_config_entry: MockConfigEntry,
# ) -> None:
#     """Test reauthentication flow with invalid credentials."""
#     with patch(
#         "custom_components.harreither.config_flow.IntegrationBlueprintApiClient"
#     ) as mock_client:
#         mock_client.return_value.async_get_data = AsyncMock(
#             side_effect=IntegrationBlueprintApiClientAuthenticationError("Invalid credentials")
#         )
#
#         result = await mock_config_entry.start_reauth_flow(hass)
#
#         assert result["type"] is FlowResultType.FORM
#         assert result["step_id"] == "reauth_confirm"
#         assert result["errors"] == {}
#
#         result = await hass.config_entries.flow.async_configure(
#             result["flow_id"],
#             user_input={CONF_PASSWORD: "wrong_password"},
#         )
#
#         assert result["type"] is FlowResultType.FORM
#         assert result["step_id"] == "reauth_confirm"
#         assert result["errors"] == {"base": "auth"}


async def test_recovery_after_error(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test recovery after initial error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # First attempt fails with connection error
    with patch(
        "custom_components.harreither.config_flow.IntegrationBlueprintApiClient"
    ) as mock_client:
        mock_client.return_value.async_get_data = AsyncMock(
            side_effect=IntegrationBlueprintApiClientCommunicationError(
                "Connection error"
            )
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "connection"}

        # Fix the mock and retry
        mock_client.return_value.async_get_data = AsyncMock(return_value={})

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == TEST_USERNAME
        assert len(mock_setup_entry.mock_calls) == 1
