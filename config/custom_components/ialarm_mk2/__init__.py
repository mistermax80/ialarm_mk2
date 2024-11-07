"""The iAlarm-MK Integration 2 integration."""

from __future__ import annotations

from asyncio.timeouts import timeout
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import iAlarmMk2Coordinator
from .hub import IAlarmMkHub

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.ALARM_CONTROL_PANEL]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up iAlarm-MK Integration 2 from a config entry."""
    _LOGGER.info("Set up iAlarm-MK 2 Integration from a config entry...")

    hub: IAlarmMkHub = IAlarmMkHub(entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

    try:
        async with timeout(10):
            await hub.validate()
    except (TimeoutError, ConnectionError) as ex:
        raise ConfigEntryNotReady from ex

    coordinator: iAlarmMk2Coordinator = iAlarmMk2Coordinator(hass, hub)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

def should_pool(self):
    '''should_pool.'''
    return False
