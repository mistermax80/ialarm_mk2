"""Config flow for iAlarm-MK Integration 2 integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import IAlarmMkHub, libpyialarmmk as ipyialarmmk
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

defaults = {
    CONF_HOST: ipyialarmmk.iAlarmMkInterface.IALARMMK_P2P_DEFAULT_HOST,
    CONF_PORT: ipyialarmmk.iAlarmMkInterface.IALARMMK_P2P_DEFAULT_PORT,
    CONF_USERNAME: "<CABxxxxxx>",
    CONF_PASSWORD: "<password>",
    CONF_SCAN_INTERVAL: 60,
}

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=defaults[CONF_HOST]): str,
        vol.Required(CONF_PORT, default=defaults[CONF_PORT]): int,
        vol.Required(CONF_USERNAME, default=defaults[CONF_USERNAME]): str,
        vol.Required(CONF_PASSWORD, default=defaults[CONF_PASSWORD]): str,
        vol.Required(CONF_SCAN_INTERVAL, default=defaults[CONF_SCAN_INTERVAL]): int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    hub = IAlarmMkHub(
        hass,
        data[CONF_HOST],
        data[CONF_PORT],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        data[CONF_SCAN_INTERVAL],
    )

    if not await hub.validate():
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": data[CONF_USERNAME]}


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for iAlarm-MK Integration 2."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                await self.async_set_unique_id(info["title"])
                self._abort_if_unique_id_configured()
            except data_entry_flow.AbortFlow:
                return self.async_abort(reason="already_configured")
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Handle the reconfigure step."""
        errors: dict[str, str] = {}

        existing_entry = self.context.get("entry")

        if not existing_entry:
            entries = self.hass.config_entries.async_entries(DOMAIN)
            existing_entry = entries[0] if entries else None

        if existing_entry:
            defaults.update(existing_entry.data)

        STEP_RECONFIGURE_DATA_SCHEMA = vol.Schema(
            {
                vol.Required(CONF_HOST, default=defaults[CONF_HOST]): str,
                vol.Required(CONF_PORT, default=defaults[CONF_PORT]): int,
                vol.Required(CONF_PASSWORD, default=defaults[CONF_PASSWORD]): str,
                vol.Required(
                    CONF_SCAN_INTERVAL, default=defaults[CONF_SCAN_INTERVAL]
                ): int,
            }
        )

        if user_input is not None:
            # Prendiamo username dall'entry esistente
            username = (
                existing_entry.data.get(CONF_USERNAME, defaults[CONF_USERNAME])
                if existing_entry
                else defaults[CONF_USERNAME]
            )

            # Ricostruiamo il dict dati completo con username
            full_data = dict(user_input)
            full_data[CONF_USERNAME] = username
            try:
                await validate_input(self.hass, full_data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    existing_entry, data=full_data
                )
                return self.async_abort(reason="reconfigured")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=STEP_RECONFIGURE_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
