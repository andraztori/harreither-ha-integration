"""Sensor platform for harreither."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.typing import StateType

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
    """Set up the sensor platform."""
    # Entity creation is now handled in __init__.py after initialization completes
    pass


class HarreitherSensor(SensorEntity):
    """Harreither Sensor class."""

    def __init__(
        self,
        entry_id: str,
        entity_key: str,
        entity_description: SensorEntityDescription,
        data_entry: dict | None = None,
    ) -> None:
        """Initialize the sensor class."""
        self.entity_description = entity_description
        self._data_entry = data_entry
        self._attr_unique_id = f"{entry_id}-{entity_key}"
        self._attr_native_value = data_entry.get("value") if data_entry else None

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return cast(StateType, self._attr_native_value)

    def update_state(self, value: float) -> None:
        """Update sensor state and write to Home Assistant."""
        self._attr_native_value = value
        self.async_write_ha_state()


class HarreitherEnumSensor(SensorEntity):
    """Harreither Enum Sensor class."""

    def __init__(
        self,
        entry_id: str,
        entity_key: str,
        entity_name: str,
        options: list[str],
        data_entry: dict | None = None,
    ) -> None:
        """Initialize the enum sensor class."""
        self._attr_unique_id = f"{entry_id}-{entity_key}"
        self._attr_name = entity_name
        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.ENUM
        self._data_entry = data_entry
        self._options = options

        # Set current value based on data_entry value (index)
        current_value = data_entry.get("value") if data_entry else 0
        if isinstance(current_value, int) and 0 <= current_value < len(options):
            self._attr_native_value = options[current_value]
        else:
            self._attr_native_value = options[0] if options else None

    @property
    def native_value(self) -> StateType:
        """Return the current enum value."""
        return cast(StateType, self._attr_native_value)

    @property
    def options(self) -> list[str]:
        """Return the list of available options for the enum."""
        return self._options

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes with current index."""
        native_str = str(self._attr_native_value) if self._attr_native_value else None
        if native_str and native_str in self._options:
            current_index = self._options.index(native_str)
        else:
            current_index = 0
        return {
            "current_index": current_index,
        }

    def update_state(self, value: int) -> None:
        """Update enum sensor state from device and write to Home Assistant."""
        if isinstance(value, int) and 0 <= value < len(self._options):
            self._attr_native_value = self._options[value]
            self.async_write_ha_state()
        else:
            LOGGER.warning(
                "Invalid value %s for enum sensor %s (valid range: 0-%s)",
                value,
                self.name,
                len(self._options) - 1,
            )
