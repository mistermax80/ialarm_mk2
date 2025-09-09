"""Diagnostic file."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

TO_REDACT = [CONF_PASSWORD, CONF_USERNAME, "title", "unique_id", "serial_number", "name"]

_LOGGER = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    _LOGGER.debug("entry: %s", entry.as_dict())

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    return {
        "id": device.id,
        "name": device.name,
        "name_by_user": device.name_by_user,
        "manufacturer": device.manufacturer,
        "model": device.model,
        "serial_number": device.serial_number,
        "area_id": device.area_id,
        "primary_config_entry": device.primary_config_entry,
        "via_device_id": device.via_device_id,
    }
