"""Test setup and host reconfiguration for Harreither."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.harreither.api import (
    HarrieitherClientAuthenticationError,
    HarrieitherClientCommunicationError,
    HarrieitherClientError,
)
from custom_components.harreither.const import CONF_AREA, DOMAIN

OLD_HOST = "192.168.1.232"
NEW_HOST = "192.168.1.202"
USER_INPUT = {
    CONF_HOST: NEW_HOST,
    CONF_USERNAME: "test_user",
    CONF_PASSWORD: "test_password",
}


async def test_user_flow(
    hass: HomeAssistant, mock_setup_entry: AsyncMock, mock_credentials: AsyncMock
) -> None:
    """Setup uses the host as the unique ID, rather than the returned device ID."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == NEW_HOST
    assert result["result"].data[CONF_HOST] == NEW_HOST
    mock_credentials.assert_awaited_once_with(
        host=NEW_HOST, username="test_user", password="test_password"
    )
    mock_setup_entry.assert_awaited_once()


async def test_user_flow_duplicate_host(
    hass: HomeAssistant, mock_credentials: AsyncMock
) -> None:
    """Setup rejects a host already used by another entry."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=NEW_HOST, data=USER_INPUT)
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize("host", [NEW_HOST, OLD_HOST])
async def test_reconfigure_host(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_credentials: AsyncMock,
    entity_registry: er.EntityRegistry,
    host: str,
) -> None:
    """Changing or retaining the host updates the existing entry and reloads it."""
    mock_config_entry.add_to_hass(hass)
    entry_id = mock_config_entry.entry_id
    entity = entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry_id}-(112, 30002, None)",
        config_entry=mock_config_entry,
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry_id},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {}

    with patch.object(hass.config_entries, "async_reload", return_value=True) as reload:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**USER_INPUT, CONF_HOST: host, CONF_AREA: "living_room"}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.entry_id == entry_id
    assert mock_config_entry.unique_id == host
    assert mock_config_entry.data[CONF_HOST] == host
    assert mock_config_entry.data["existing_setting"] == "preserved"
    assert mock_config_entry.data[CONF_AREA] == "living_room"
    assert entity_registry.async_get(entity.entity_id) == entity
    mock_credentials.assert_awaited_once_with(
        host=host, username="test_user", password="test_password"
    )
    reload.assert_awaited_once_with(entry_id)


async def test_reconfigure_duplicate_host(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_credentials: AsyncMock,
) -> None:
    """A duplicate destination host leaves both entries untouched."""
    mock_config_entry.add_to_hass(hass)
    other_entry = MockConfigEntry(domain=DOMAIN, unique_id=NEW_HOST, data=USER_INPUT)
    other_entry.add_to_hass(hass)
    original_data = dict(mock_config_entry.data)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry.entry_id,
        },
    )
    with patch.object(hass.config_entries, "async_reload", return_value=True) as reload:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.unique_id == OLD_HOST
    assert mock_config_entry.data == original_data
    assert other_entry.unique_id == NEW_HOST
    assert other_entry.data == USER_INPUT
    reload.assert_not_called()


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (HarrieitherClientAuthenticationError("invalid"), "auth"),
        (HarrieitherClientCommunicationError("unreachable"), "connection"),
        (HarrieitherClientError("unexpected"), "unknown"),
    ],
)
@pytest.mark.parametrize(
    "source", [config_entries.SOURCE_USER, config_entries.SOURCE_RECONFIGURE]
)
async def test_validation_failure_and_recovery(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: AsyncMock,
    mock_credentials: AsyncMock,
    exception: Exception,
    error: str,
    source: str,
) -> None:
    """Failed validation does not change the entry, and the form can be retried."""
    context = {"source": source}
    if source == config_entries.SOURCE_RECONFIGURE:
        mock_config_entry.add_to_hass(hass)
        context["entry_id"] = mock_config_entry.entry_id
    original_data = dict(mock_config_entry.data)
    result = await hass.config_entries.flow.async_init(DOMAIN, context=context)
    mock_credentials.side_effect = exception

    with patch.object(hass.config_entries, "async_reload", return_value=True) as reload:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": error}
        assert mock_config_entry.data == original_data
        assert mock_config_entry.unique_id == OLD_HOST
        reload.assert_not_called()
        mock_setup_entry.assert_not_called()

        mock_credentials.side_effect = None
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
        await hass.async_block_till_done()

    if source == config_entries.SOURCE_RECONFIGURE:
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"
        assert mock_config_entry.unique_id == NEW_HOST
        reload.assert_awaited_once_with(mock_config_entry.entry_id)
    else:
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["result"].unique_id == NEW_HOST
        mock_setup_entry.assert_awaited_once()


async def test_reconfigure_repeated_address_changes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_credentials: AsyncMock,
) -> None:
    """The same entry can change IP again after the first reconfiguration."""
    mock_config_entry.add_to_hass(hass)
    entry_id = mock_config_entry.entry_id
    with patch.object(hass.config_entries, "async_reload", return_value=True) as reload:
        for host in (NEW_HOST, "192.168.1.203"):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": config_entries.SOURCE_RECONFIGURE,
                    "entry_id": entry_id,
                },
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {**USER_INPUT, CONF_HOST: host}
            )
            await hass.async_block_till_done()
            assert result["type"] is FlowResultType.ABORT
            assert result["reason"] == "reconfigure_successful"
            assert mock_config_entry.unique_id == host
            assert mock_config_entry.data[CONF_HOST] == host
            assert mock_config_entry.entry_id == entry_id
    assert reload.await_count == 2
