"""The iAlarm-MK Integration 2 integration."""

from __future__ import annotations

from asyncio.timeouts import timeout
from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    STATE_UNAVAILABLE,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import libpyialarmmk as ipyialarmmk
from .binary_sensor import IAlarmmkSensor
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up iAlarm-MK Integration 2 from a config entry."""
    _LOGGER.info("Set up iAlarm-MK Integration 2 from a config entry.")

    hub: IAlarmMkHub = IAlarmMkHub(entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

    try:
        async with timeout(10):
            mac: str = await hub.get_mac()
            _LOGGER.info("MAC: %s", mac)
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

class IAlarmMkHub:
    """IAlarmMkHub."""

    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        """Initialize."""
        _LOGGER.info("Initialize IAlarmMkHub")
        self.host: str = host
        self.port: int = port
        self.username: str = username
        self.password: str = password
        self.mac: str = None
        self.ialarmmk = ipyialarmmk.iAlarmMkInterface(self.username, self.password, self.host, self.port, None, _LOGGER)

    async def get_mac(self) -> str:
        """Test if we can authenticate with the host."""
        _LOGGER.debug("IAlarmMkHub.get_mac")
        if self.mac is None:
            self.mac = format_mac(self.ialarmmk.get_mac())
        _LOGGER.debug("MAC: %s", self.mac)
        return self.mac

    async def validate(self) -> bool:
        """Test if we can authenticate with the host."""
        _LOGGER.debug("IAlarmMkHub.validate")
        await self.get_mac()
        return True

class iAlarmMk2Coordinator(DataUpdateCoordinator):
    """Class to manage fetching iAlarm-MK data."""

    def __init__(
        self, hass: HomeAssistant, hub: IAlarmMkHub
    ) -> None:
        """Initialize global a iAlarm-MK 2 data updater."""
        _LOGGER.info("Initialize global a iAlarm-MK 2 data updater.")
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            #update_interval=SCAN_INTERVAL,
            update_interval=timedelta(seconds=60),
        )
        self.hub: IAlarmMkHub = hub
        self.hass = hass
        self.sensors:IAlarmmkSensor = []

    async def _async_setup(self):
        _LOGGER.info("Setup iAlarm-MK 2 data updater.")
        SENSOR_CONFIG = []
        try:
            self.hub.ialarmmk.ialarmmkClient.login()
            _LOGGER.debug("Login OK.")
            idsSensors = self.hub.ialarmmk.ialarmmkClient.GetSensor()
            _LOGGER.debug("Retrieve sensors list OK.")
            zones = self.hub.ialarmmk.ialarmmkClient.GetZone()
            _LOGGER.debug("Retrieve zones list OK.")
            self.hub.ialarmmk.ialarmmkClient.logout()
            _LOGGER.debug("Logout OK.")

            for index, id_sensor in enumerate(idsSensors):
                if id_sensor:
                    sensor = {
                        "index": index,
                        "unique_id": id_sensor,
                        "entity_id": f"binary_sensor.{DOMAIN}_{zones[index].get("Name", "no name")}",
                        "name": zones[index].get("Name", "no name"),
                        "zone_type": int(zones[index].get("Type", 0)),
                    }
                    SENSOR_CONFIG.append(sensor)

        except Exception:
                _LOGGER.exception("Error in setup entities.")

        for sc in SENSOR_CONFIG:
            iAlarmSensor = IAlarmmkSensor(self, sc["name"], sc["index"], sc["entity_id"], sc["unique_id"], sc["zone_type"])
            self.sensors.append(iAlarmSensor)

    async def _async_update_data(self) -> None:
        """Fetch data from iAlarm-MK 2."""
        _LOGGER.info("Fetching data.")
        tz = ZoneInfo(self.hass.config.time_zone)
        current_time = datetime.now(tz)
        try:
            async with timeout(12):
                self.hub.ialarmmk.ialarmmkClient.login()
                _LOGGER.debug("Login OK.")
                status = self.hub.ialarmmk.ialarmmkClient.GetByWay()
                _LOGGER.debug("Retrive last sensors status.")
                _LOGGER.debug("Status: %s",status)

                # Inizializza un messaggio di log
                log_message = "\n"

                for _idx, sensor in enumerate(self.sensors):
                    sensor: IAlarmmkSensor
                    state: int = status[int(sensor.index)]

                    log_message += f"{sensor.name}: state "

                    # Verifica se la zona è in uso e in errore
                    if state & self.hub.ialarmmk.ZONE_IN_USE and state & self.hub.ialarmmk.ZONE_FAULT:
                        sensor.set_attr_is_on(True)
                        log_message += f"(Aperto) {bin(state)} \n"
                    # Verifica se la zona è solo in uso
                    elif state & self.hub.ialarmmk.ZONE_IN_USE:
                        sensor.set_attr_is_on(False)
                        log_message += f"(Chiuso) {bin(state)} \n"
                    # Verifica se la zona non è utilizzata
                    elif state == self.hub.ialarmmk.ZONE_NOT_USED:
                        sensor.set_attr_is_on(None)
                        sensor.set_state(STATE_UNAVAILABLE)
                        log_message += f"(Non Usato) {bin(state)} \n"
                    else:
                        sensor.set_attr_is_on(None)
                        _LOGGER.warning("%s: state (Sconosciuto) %s \n", sensor.name, bin(state))

                    # Aggiorna gli attributi di stato extra
                    sensor.set_extra_state_attributes(
                        bool(state & self.hub.ialarmmk.ZONE_LOW_BATTERY),
                        bool(state & self.hub.ialarmmk.ZONE_LOSS),
                        bool(state & self.hub.ialarmmk.ZONE_BYPASS),
                        current_time
                    )
                # Logga il messaggio finale
                _LOGGER.debug(log_message)

        except Exception as error:
            _LOGGER.exception("Error during fetch data.")
            self.hub.ialarmmk.ialarmmkClient.logout()
            _LOGGER.debug("*** Logout OK ***")
            raise UpdateFailed(error) from error
