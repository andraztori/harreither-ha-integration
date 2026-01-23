"""Binary sensor platform for harreither """

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .const import LOGGER
from .data import HarreitherConfigEntry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HarreitherConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    # Entity creation is now handled in __init__.py after initialization completes
    pass


class HarreitherBinarytSensor(BinarySensorEntity):
    """Harreither binary_sensor class."""

    def __init__(
        self,
        entry_id: str,
        entity_key: str,
        entity_description: BinarySensorEntityDescription,
        data_entry: dict | None = None,
    ) -> None:
        """Initialize the binary_sensor class."""
        self.entity_description = entity_description
        self._data_entry = data_entry
        self._attr_unique_id = f"{entry_id}-{entity_key}"
        self._attr_is_on: bool = (data_entry.get("value") == 1) if data_entry else False

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self._attr_is_on

    def update_state(self, value: int) -> None:
        """Update binary sensor state and write to Home Assistant."""
        self._attr_is_on = value == 1
        self.async_write_ha_state()
