"""Config flow for iAlarm-MK Integration 2 integration."""

from __future__ import annotations

import datetime
import logging
from typing import Any

import voluptuous as vol
from homeassistant import data_entry_flow
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from . import IAlarmMkHub
from . import libpyialarmmk as ipyialarmmk
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


class MyConfigFlow(ConfigFlow, domain=DOMAIN):
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

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> MyOptionsFlowHandler:
        """Create the options flow."""
        return MyOptionsFlowHandler()


class MyOptionsFlowHandler(OptionsFlow):
    """Options Flow per configurare dettagli per i sensori."""

    async def async_step_init(self, user_input=None):
        """Gestisce il form delle opzioni."""
        _LOGGER.debug("Options flow invoked with user_input=%r", user_input)

        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        sensors = coordinator.data.sensors_data
        _LOGGER.debug("Options flow sensors: %s", len(sensors))
        errors: dict[str, str] = {}

        if user_input is not None:
            _LOGGER.debug("Starting validation loop")
            clean_data = {}

            for sensor in sensors:
                key = f"last_battery_change_{sensor.unique_id}"
                label = f"{sensor.zone_name} (zona {sensor.index + 1})"
                clear_key = (
                    f"Nessuna data — {sensor.zone_name} (zona {sensor.index + 1})"
                )

                clear_selected = user_input.get(clear_key, False)

                _LOGGER.debug(
                    "Checking sensor %s (%s), checkbox=%r",
                    sensor.unique_id,
                    sensor.zone_name,
                    clear_selected,
                )

                # La checkbox ha priorità assoluta sulla data.
                if clear_selected:
                    clean_data[key] = ""
                    continue

                raw_value = user_input.get(label)

                # Campo vuoto: nessuna data salvata.
                if not raw_value:
                    clean_data[key] = ""
                    continue

                try:
                    parsed_date = datetime.date.fromisoformat(str(raw_value))

                    if parsed_date > dt_util.now().date():
                        errors[label] = "future_date"
                    else:
                        clean_data[key] = parsed_date.isoformat()

                except (ValueError, TypeError):
                    errors[label] = "data_invalid"

            if not errors:
                _LOGGER.debug("Saving battery replacement dates: %s", clean_data)
                return self.async_create_entry(title="", data=clean_data)

        schema_dict = {
            vol.Optional(
                "Istruzioni",
                default=(
                    "Seleziona la data dell'ultima sostituzione della batteria. "
                    "Se non la conosci, seleziona l'opzione per disabilitare "
                    "la stima della batteria."
                ),
            ): selector.TextSelector(
                selector.TextSelectorConfig(read_only=True, multiline=True)
            )
        }

        for sensor in sensors:
            key = f"last_battery_change_{sensor.unique_id}"
            label = f"{sensor.zone_name} (zona {sensor.index + 1})"
            clear_key = f"Nessuna data — {sensor.zone_name} (zona {sensor.index + 1})"

            saved_date = self.config_entry.options.get(key, "")

            # Conserva il valore inviato se il form viene ripresentato
            # dopo un errore; altrimenti usa la data salvata.
            if user_input is not None and label in user_input:
                default_date = user_input[label] or saved_date or "1970-01-01"
            else:
                default_date = saved_date or "1970-01-01"

            if user_input is not None and clear_key in user_input:
                default_clear = user_input[clear_key]
            else:
                default_clear = not bool(saved_date)

            # Campo data. 1970-01-01 è un workaround temporaneo
            # per evitare il valore iniziale nullo non accettato.
            schema_dict[vol.Optional(label, default=default_date)] = (
                selector.DateSelector(selector.DateSelectorConfig())
            )

            # Checkbox per indicare che non è disponibile una data.
            schema_dict[vol.Optional(clear_key, default=default_clear)] = (
                selector.BooleanSelector(selector.BooleanSelectorConfig())
            )

        _LOGGER.debug("Options form schema keys: %s", list(schema_dict.keys()))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
