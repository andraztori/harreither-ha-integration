"""Adds config flow for Harreither."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import (
    HarrieitherClientAuthenticationError,
    HarrieitherClientCommunicationError,
    HarrieitherClientError,
)
from .const import DOMAIN, LOGGER
from harreither_brain_client.connection import Connection
from .__init__ import get_url_from_host


class HarreitherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Harreither."""

    VERSION = 1
    MINOR_VERSION = 1

    def _build_schema(self, defaults: dict | None = None) -> vol.Schema:
        """Return form schema with optional defaults."""

        defaults = defaults or {}

        return vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=defaults.get(CONF_HOST, vol.UNDEFINED),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    ),
                ),
                vol.Required(
                    CONF_USERNAME,
                    default=defaults.get(CONF_USERNAME, vol.UNDEFINED),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    ),
                ),
                vol.Required(CONF_PASSWORD): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD,
                    ),
                ),
            },
        )

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        #        raise Exception("test")
        if user_input is not None:
            try:
                device_id = await self._test_credentials(
                    host=user_input[CONF_HOST],
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except HarrieitherClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except HarrieitherClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except HarrieitherClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=user_input,
                )

        # Prepare defaults for form, including discovered host if available
        defaults = {}
        if not defaults.get(CONF_HOST) and "discovered_host" in self.context:
            defaults[CONF_HOST] = self.context["discovered_host"]

        return self.async_show_form(
            step_id="user",
            data_schema=self._build_schema(defaults),
            errors=_errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> config_entries.ConfigFlowResult:
        """Handle zeroconf discovery."""
        LOGGER.debug("Zeroconf discovery_info: %s", discovery_info)

        # Extract host from discovery info
        host = discovery_info.host

        # Set unique ID based on the device host
        # We could in theory use discovery_info.name, but that's hard to align with manual entry
        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()

        # Store discovered host in context for prefilling the form
        self.context["discovered_host"] = host

        return await self.async_step_user(user_input=None)

    async def async_step_reconfigure(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a reconfiguration flow initiated from the entry."""

        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            try:
                device_id = await self._test_credentials(
                    host=user_input[CONF_HOST],
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except HarrieitherClientAuthenticationError as exception:
                LOGGER.warning(exception)
                errors["base"] = "auth"
            except HarrieitherClientCommunicationError as exception:
                LOGGER.error(exception)
                errors["base"] = "connection"
            except HarrieitherClientError as exception:
                LOGGER.exception(exception)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=user_input,
                    reason="reconfigure_successful",
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._build_schema(entry.data),
            errors=errors,
        )

    async def _test_credentials(self, host: str, username: str, password: str) -> str:
        """Validate credentials and return the device id."""
        ws_url = get_url_from_host(host)

        conn_obj = Connection()
        device_id: str | None = None
        try:
            try:
                await conn_obj.async_websocket_connect(ws_url, proxy_url=None)
            except Exception as err:  # noqa: BLE001
                raise HarrieitherClientCommunicationError(
                    f"Failed to connect websocket: {err}"
                ) from err

            try:
                await conn_obj.establish_secure_connection()
            except Exception as err:  # noqa: BLE001
                raise HarrieitherClientCommunicationError(
                    f"Failed to establish secure connection: {err}"
                ) from err

            try:
                success = await conn_obj.authentication_obj.execute_authentication_now(
                    username, password
                )
            except Exception as err:  # noqa: BLE001
                raise HarrieitherClientError(
                    f"Authentication attempt failed unexpectedly: {err}"
                ) from err

            if not success:
                raise HarrieitherClientAuthenticationError("Invalid credentials")

            device_id = conn_obj.device_id
            if not device_id:
                raise HarrieitherClientError(
                    "Device id missing from controller response"
                )
        finally:
            await conn_obj.async_close()

        return device_id
