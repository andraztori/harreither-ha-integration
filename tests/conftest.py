"""Test configuration for Harreither integration."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

# Add custom components path to sys.path
CUSTOM_COMPONENTS_PATH = Path(__file__).parent.parent.parent.parent / "config"
if str(CUSTOM_COMPONENTS_PATH) not in sys.path:
    sys.path.insert(0, str(CUSTOM_COMPONENTS_PATH))


@pytest.fixture(autouse=True)
def enable_custom_integrations(hass: HomeAssistant) -> None:
    """Enable custom integrations by clearing the cache."""
    # Clear custom components cache to allow discovery
    hass.data.pop("custom_components", None)


@pytest.fixture
def mock_setup_entry() -> AsyncMock:
    """Override async_setup_entry."""
    with patch(
        "custom_components.harreither.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return the default mocked config entry."""
    from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

    mock_config_entry = MockConfigEntry(
        domain="harreither",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
        },
        unique_id="test-user",  # slugified version
        title="test_user",
    )
    return mock_config_entry
