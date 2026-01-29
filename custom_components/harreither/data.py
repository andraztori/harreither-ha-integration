"""Custom types for Harreither."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio import Task

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

from .brain import Connection


type HarreitherConfigEntry = ConfigEntry[HarreitherData]


@dataclass
class HarreitherData:
    """Data for the Harreither integration."""

    integration: Integration
    entities: dict = field(
        default_factory=dict
    )  # Dictionary mapping entity keys to entity objects
    connection: Connection | None = (
        None  # Connection object from harreither_brain_client
    )
    connection_task: Task | None = None  # Task running the connection loop
    platform_dict: dict = field(
        default_factory=dict
    )  # Dictionary mapping platform domains to platform objects
