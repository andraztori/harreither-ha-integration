"""Fixtures for the Harreither integration."""

import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load the custom integration."""


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Prevent the integration from connecting to a real controller."""
    with patch(
        "custom_components.harreither.async_setup_entry", return_value=True
    ) as mock:
        yield mock


@pytest.fixture
def mock_credentials() -> Generator[AsyncMock]:
    """Authenticate without connecting; the device ID differs from the host."""
    with patch(
        "custom_components.harreither.config_flow.HarreitherConfigFlow._test_credentials",
        return_value="controller-device-id",
    ) as mock:
        yield mock


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return an existing entry using the controller's old IP as its identity."""
    return MockConfigEntry(
        domain="harreither",
        data={
            CONF_HOST: "192.168.1.232",
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            "existing_setting": "preserved",
        },
        unique_id="192.168.1.232",
        title="test_user",
    )
