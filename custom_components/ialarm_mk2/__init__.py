"""The iAlarm-MK Integration 2 integration."""

from __future__ import annotations

from asyncio.timeouts import timeout
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
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
    _LOGGER.info("Set up %s Integration from a config entry...", DOMAIN)

    # Assicuriamoci che unique_id sia sempre settato (migrazione "al volo" in setup)
    if entry.unique_id is None:
        unique_id = entry.data.get(CONF_USERNAME)
        if unique_id:
            _LOGGER.debug(
                "Setting unique_id for entry %s: %s", entry.entry_id, unique_id
            )
            hass.config_entries.async_update_entry(entry, unique_id=unique_id)

    entry.async_on_unload(entry.add_update_listener(async_update_entry))

    hub: IAlarmMkHub = IAlarmMkHub(
        hass,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_SCAN_INTERVAL],
    )

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


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Gestisce la riconfigurazione."""
    _LOGGER.info("Update %s Integration from a config entry...", DOMAIN)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unload %s Integration from a config entry...", DOMAIN)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry versions to new versions."""

    _LOGGER.debug("Starting migration for %s version %s", DOMAIN, entry.version)

    if entry.unique_id is None:
        unique_id = entry.data.get(CONF_USERNAME)
        if unique_id:
            _LOGGER.debug(
                "Setting unique_id for migrated entry %s: %s", entry.entry_id, unique_id
            )
            hass.config_entries.async_update_entry(entry, unique_id=unique_id)

    if entry.version < 2:
        data = dict(entry.data)
        data.setdefault(CONF_SCAN_INTERVAL, 60)
        ret: bool = hass.config_entries.async_update_entry(
            entry,
            data=data,
            version=2,
            # Ecco l’aggiunta di minor_version:
            options=entry.options,
            # Usare async_update_entry non supporta minor_version direttamente,
            # quindi si può aggiornare con async_update_entry ma la chiave minor_version
            # va scritta direttamente nel file .storage o gestita da HA internamente
        )
        _LOGGER.info("Migration to version 2 complete (result=%s).", ret)

    # Se serve aggiornare anche il minor_version, purtroppo ConfigEntry non espone API diretta,
    # ma HA la gestisce internamente. In alternativa, se serve assolutamente, puoi manipolare
    # direttamente .storage/core.config_entries (non consigliato).

    return True
