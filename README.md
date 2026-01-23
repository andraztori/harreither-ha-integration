# Harreither Brain for Home Assistant

Custom integration that connects a Harreither Brain controller to Home Assistant. It authenticates with the controller, listens for live updates, and creates sensors and binary sensors dynamically based on the data the controller exposes.

## Features
- Native config flow: add the integration from Home Assistant UI (no YAML needed).
- Live updates: websocket connection keeps entities in sync without polling.
- Automatic entity creation:
	- Temperature sensors when the device reports `°C` values.
	- Humidity sensors when the device reports percentage values.
	- Binary sensors when the device exposes two-state elements.
	- Enum sensors for multi-state elements (e.g., modes) with descriptive options.
- Reconnect and backoff logic so the integration retries when the controller drops.

## Requirements
- A reachable Harreither Brain controller on your network.
- Controller credentials (username and password).

## Installation
You can install manually or via HACS as a custom repository.

### Manual install
1. Copy the `custom_components/harreither` directory into your Home Assistant `custom_components` folder.
2. Restart Home Assistant to load the integration.

### HACS (custom repository)
1. In HACS, add this repository URL as a custom integration source: `https://github.com/andraztori/harreither-ha-integration`.
2. Install the **Harreither Brain** integration.
3. Restart Home Assistant.

## Configuration (UI)
1. In Home Assistant, go to *Settings → Devices & Services* and click *Add Integration*.
2. Search for **Harreither Brain**.
3. Enter:
	 - **Host**: the controller address (IP/hostname). Use `ws://` or `wss://` if you prefer to specify the scheme explicitly.
	 - **Username** and **Password** for the controller.
4. Submit to finish. The integration will validate the credentials, store a unique device ID, and start the websocket connection.

## Entities created automatically
- Temperature sensors (device class `temperature`, unit `°C`).
- Humidity sensors (device class `humidity`, unit `%`).
- Binary sensors for two-state elements.
- Enum sensors for elements with more than two states; options are populated from the controller metadata.
- There are many missing sensors not yet supported

Entities are added dynamically when the controller reports them. Live value changes are pushed over the websocket and reflected immediately in Home Assistant.

## Connectivity and reliability
- The integration establishes a secure websocket session to the controller.
- If the connection drops, it retries with a backoff schedule (immediate, then 5s, 10s, 60s) and clears/re-creates entities as needed.
- Authentication is retried as part of the reconnection loop.

## Troubleshooting
- Invalid credentials will be flagged during setup; reconfigure the entry from *Devices & Services* if they change.
