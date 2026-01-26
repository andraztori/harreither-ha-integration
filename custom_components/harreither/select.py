"""Select platform for harreither."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription

from .const import LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    # Entity creation is handled in __init__.py after initialization completes
    pass


class HarreitherInputSelect(SelectEntity):
    """Harreither Select entity."""

    entity_description: SelectEntityDescription

    def __init__(
        self,
        entry_id: str,
        entity_key: str,
        entity_description: SelectEntityDescription,
        data_entry: dict | None = None,
    ) -> None:
        """Initialize the select entity."""
        self.entity_description = entity_description
        self._attr_unique_id = f"{entry_id}-{entity_key}"
        self._attr_has_entity_name = True
        self._data_entry = data_entry

        current_value = data_entry.get("value") if data_entry else 0
        if isinstance(current_value, int) and 0 <= current_value < len(
            entity_description.options
        ):
            self._attr_current_option = entity_description.options[current_value]
        else:
            self._attr_current_option = (
                entity_description.options[0] if entity_description.options else None
            )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option in self.entity_description.options:
            self._attr_current_option = option
            self.async_write_ha_state()
            LOGGER.info("Select %s set to %s", self.entity_description.name, option)
        else:
            LOGGER.warning(
                "Option %s not in available options for %s",
                option,
                self.entity_description.name,
            )

    def update_state(self, value: int) -> None:
        """Update select state and write to Home Assistant."""
        if isinstance(value, int) and 0 <= value < len(self.entity_description.options):
            self._attr_current_option = self.entity_description.options[value]
            self.async_write_ha_state()
        else:
            LOGGER.warning(
                "Invalid index %s for select %s",
                value,
                self.entity_description.name,
            )
