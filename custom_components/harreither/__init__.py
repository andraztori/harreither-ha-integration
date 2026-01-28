"""Custom integration to integrate Harreither with Home Assistant."""

from __future__ import annotations

import asyncio
import traceback
import websockets
from contextlib import suppress
from functools import partial
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.helpers.entity_platform import async_get_platforms
from homeassistant.helpers import entity_registry
from homeassistant.loader import async_get_loaded_integration

from .const import DOMAIN, LOGGER
from .data import HarreitherData
from .connection import Connection
from .binary_sensor import HarreitherBinarytSensor
from .select import HarreitherInputSelect
from .sensor import HarreitherEnumSensor, HarreitherSensor

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import HarreitherConfigEntry

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SENSOR,
]


async def async_add_entity(
    hass: HomeAssistant,
    entry: HarreitherConfigEntry,
    platform_dict: dict,
    dict_key,
    data_entry: Entry,
) -> None:
    """Add a single entity based on data_entry type."""

    screen_key = data_entry["_screen_key"]
    entity_key = repr(dict_key) + repr(screen_key)
    if entry.runtime_data.entities.get(entity_key):
        LOGGER.error(
            "Entity %s already exists, skipping creation",
            entity_key,
        )
        return
    # Determine a user-friendly name with sensible fallbacks
    # 1) use provided name
    # 2) fallback to _vid_obj["text"] if available
    # 3) fallback to the key
    # 4) finally use "Unknown"
    _vid_obj = data_entry.get("_vid_obj")  # hard fail if it is not there
    if not _vid_obj:
        LOGGER.warning(
            "Data entry for key %s is missing _vid_obj: %s",
            entity_key,
            data_entry,
        )
        return
    # Prefix sensor names with screen title when available
    screen_prefix: str = ""
    conn = entry.runtime_data.connection
    screen = conn.data.screens[screen_key]
    screen_prefix = screen.get("title").strip()
    entity_name = (
        screen_prefix
        + " / "
        + data_entry.get("name", "")  # + " " + _vid_obj.get("text")
    )

    value = data_entry.get("value")

    # Determine platforms
    sensor_platform = platform_dict.get(Platform.SENSOR)
    binary_sensor_platform = platform_dict.get(Platform.BINARY_SENSOR)
    input_select_platform = platform_dict.get(Platform.SELECT)

    # Organize detection as if/elif chain and log when nothing matches
    created = False

    if _vid_obj.get("unit") == "°C" and _vid_obj.get("type") == 12 and sensor_platform:
        if not isinstance(value, (int, float)):
            LOGGER.warning(
                "Skipping temperature entity %s (key %s); value not numeric: %s",
                entity_name,
                entity_key,
                value,
            )
            return
        if isinstance(value, int):
            data_entry["value"] = float(value)
        # Temperature sensor
        LOGGER.info("Detected temperature sensor entity: %s", entity_name)
        entity_description = SensorEntityDescription(
            key=entity_key,
            name=f"{entity_name} Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        )
        sensor = HarreitherSensor(
            entry_id=entry.entry_id,
            entity_key=entity_key,
            entity_description=entity_description,
            data_entry=data_entry,
        )
        entry.runtime_data.entities[entity_key] = sensor
        try:
            await sensor_platform.async_add_entities([sensor])
        except:
            pass
        created = True

    elif _vid_obj.get("unit") == "%" and sensor_platform:
        # Humidity sensor
        LOGGER.info("Detected humidity sensor entity: %s", entity_name)
        humidity_description = SensorEntityDescription(
            key=entity_key,
            name=f"{entity_name} Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            native_unit_of_measurement=PERCENTAGE,
        )
        humidity_sensor = HarreitherSensor(
            entry_id=entry.entry_id,
            entity_key=entity_key,
            entity_description=humidity_description,
            data_entry=data_entry,
        )
        entry.runtime_data.entities[entity_key] = humidity_sensor
        await sensor_platform.async_add_entities([humidity_sensor])
        created = True

    elif _vid_obj.get("type") == 15:
        # Type 15: either binary sensor (2 elements), enum sensor (>2 elements), or select (editable)
        elements = _vid_obj.get("elements", [])

        # Check if this should be a select (if main object has edit=True)
        if data_entry.get("edit") is True:
            LOGGER.info(
                "Detected select entity with %s options: %s",
                len(elements),
                entity_name,
            )
            options = [
                elem.get("text", f"Option {i}") if isinstance(elem, dict) else str(elem)
                for i, elem in enumerate(elements)
            ]
            select_description = SelectEntityDescription(
                key=entity_key,
                name=f"{entity_name}",
                options=options,
            )
            input_select = HarreitherInputSelect(
                entry_id=entry.entry_id,
                entity_key=entity_key,
                entity_description=select_description,
                data_entry=data_entry,
                runtime_data=entry.runtime_data,
            )
            entry.runtime_data.entities[entity_key] = input_select
            await input_select_platform.async_add_entities([input_select])
            created = True
        elif len(elements) == 2 and binary_sensor_platform:
            LOGGER.info("Detected binary sensor entity: %s", entity_name)
            entity_description = BinarySensorEntityDescription(
                key=entity_key,
                name=entity_name,
                device_class=None,
            )
            binary_sensor = HarreitherBinarytSensor(
                entry_id=entry.entry_id,
                entity_key=entity_key,
                entity_description=entity_description,
                data_entry=data_entry,
            )
            entry.runtime_data.entities[entity_key] = binary_sensor
            await binary_sensor_platform.async_add_entities([binary_sensor])
            created = True
        elif len(elements) > 2 and sensor_platform:
            LOGGER.info(
                "Detected enum sensor with %s options: %s",
                len(elements),
                entity_name,
            )
            options = [
                elem.get("text", f"Option {i}") if isinstance(elem, dict) else str(elem)
                for i, elem in enumerate(elements)
            ]
            enum_sensor = HarreitherEnumSensor(
                entry_id=entry.entry_id,
                entity_key=entity_key,
                entity_name=f"{entity_name}",
                options=options,
                data_entry=data_entry,
            )
            entry.runtime_data.entities[entity_key] = enum_sensor
            await sensor_platform.async_add_entities([enum_sensor])
            created = True

    if not created:
        LOGGER.info(
            "No entity setup for %s (key %s); _vid_obj=%s",
            entity_name,
            entity_key,
            _vid_obj,
        )


async def async_remove_all_entries(
    hass: HomeAssistant,
    entry: HarreitherConfigEntry,
) -> None:
    """Remove all active entities and reset connection for restart.

    This function should be called when we need to restart the connection.
    It removes all tracked entities and clears the runtime data.
    """
    LOGGER.info("Removing all active entries for connection restart")

    # Get registry to remove entities
    registry = entity_registry.async_get(hass)

    # Remove all entities tracked in runtime data
    for entity_key, entity in entry.runtime_data.entities.items():
        try:
            entity_id = entity.entity_id
            if entity_id and entity_id in registry.entities:
                registry.async_remove(entity_id)
                LOGGER.debug("Removed entity: %s", entity_id)
        except Exception as e:  # noqa: BLE001
            LOGGER.warning(
                "Failed to remove entity %s: %s",
                entity_key,
                e,
            )

    # Clear entities dictionary
    entry.runtime_data.entities.clear()

    # Reset connection state
    entry.runtime_data.connection = None

    LOGGER.info("All active entries have been removed")


def get_url_from_host(host: str) -> str:
    """Return websocket URL built from the provided host string."""
    if host.startswith(("ws://", "wss://")):
        return host
    return f"ws://{host}"


async def _async_notify_update_callback(
    hass: HomeAssistant,
    entry: HarreitherConfigEntry,
    key: tuple,
    entry_data: Entry,
    new: bool,
) -> None:
    """Handle update callbacks from the client."""
    if key == (317, 1, None):  # this is system time 1-second ping
        return

    if key[1] == 0:  # this is jsut a break/back button
        return
    # If this is a new entity, add it dynamically
    if new:
        await async_add_entity(
            hass, entry, entry.runtime_data.platform_dict, key, entry_data
        )

    value = entry_data.get("value")
    screen_key = entry_data["_screen_key"]
    entity_key = repr(key) + repr(screen_key)

    # Look up entity directly in the entities dict
    entity = entry.runtime_data.entities.get(entity_key)
    if entity:
        entity.update_state(value)
        LOGGER.info(
            "Updated entity %s with value: %s",
            entity_key,
            value,
        )
    else:
        LOGGER.debug(
            "Entity %s not found in entities dict, value: %s (type: %s)",
            entity_key,
            value,
            type(value),
        )


async def _connection_loop(
    hass: HomeAssistant,
    entry: HarreitherConfigEntry,
) -> None:
    """Run the connection loop with reconnection logic."""
    LOGGER.info("Starting connection loop")
    ws_url = get_url_from_host(entry.data[CONF_HOST])
    retry_count = 0
    backoff_delays = [0, 5, 10, 60]  # immediate, 5s, 10s, 1 minute

    while True:
        try:
            # Calculate backoff delay
            if retry_count > 0:
                delay_index = min(retry_count - 1, len(backoff_delays) - 1)
                delay = backoff_delays[delay_index]
                if delay > 0:
                    LOGGER.info(
                        "Waiting %s seconds before reconnection attempt %s",
                        delay,
                        retry_count + 1,
                    )
                    await asyncio.sleep(delay)

            # Remove all active entries before reconnecting
            await async_remove_all_entries(hass, entry)

            conn_obj = Connection(traverse_screens_on_init=True)
            conn_obj.add_async_notify_update_callback(
                partial(_async_notify_update_callback, hass, entry)
            )
            try:
                await conn_obj.async_websocket_connect(ws_url, proxy_url=None)

                entry.runtime_data.connection = conn_obj

                await conn_obj.establish_secure_connection()
                await conn_obj.enqueue_authentication_flow(
                    username=entry.data[CONF_USERNAME],
                    password=entry.data[CONF_PASSWORD],
                )

                retry_count = 0  # Reset retry count on successful connection
                try:
                    await conn_obj.messages_process()
                except asyncio.CancelledError:
                    LOGGER.info("Connection loop cancelled, closing websocket")
                    raise
            finally:
                await conn_obj.async_close()
        except (asyncio.CancelledError, websockets.exceptions.ConnectionClosedOK):
            # Re-raise cancellation to properly exit the task
            LOGGER.info("Connection task cancelled")
            raise
        except Exception as e:  # noqa: BLE001
            retry_count += 1
            LOGGER.info("Error during connection, restarting)")
            LOGGER.info("Exception details: %s", e, exc_info=True)
            # Continue to retry with backoff
            continue


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: HarreitherConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    entry.runtime_data = HarreitherData(
        integration=async_get_loaded_integration(hass, entry.domain),
    )

    # make sure platform_dict is setup before we start the loop - as (in theory) we could be immediately adding new entries
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Get platforms and store them in runtime data for later use
    platforms = async_get_platforms(hass, DOMAIN)
    entry.runtime_data.platform_dict = {
        platform.domain: platform for platform in platforms
    }

    # Start the connection task as a background task
    task = hass.async_create_background_task(
        _connection_loop(
            hass,
            entry,
        ),
        name="_connection_loop",
    )
    entry.runtime_data.connection_task = task

    # Clean up on unload
    def _cancel_task() -> None:
        """Cancel the connection task."""
        if task and not task.done():
            task.cancel()

    entry.async_on_unload(_cancel_task)

    # Wait for initial setup to complete (optional, can be commented out to avoid startup delay)
    # await asyncio.wait_for(connection.event_initial_setup_complete.wait(), timeout=30.0)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    LOGGER.info("Finished async_setup_entry")
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: HarreitherConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    # Cancel the connection task if it exists
    if hasattr(entry.runtime_data, "connection_task"):
        task = entry.runtime_data.connection_task
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: HarreitherConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
