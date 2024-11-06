'''Coordinator.'''

from asyncio.timeouts import timeout
from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .binary_sensor import IAlarmmkSensor
from .const import DOMAIN
from .hub import IAlarmMkHub

_LOGGER = logging.getLogger(__name__)

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
        self.hub.ialarmmk.set_callback(self.callback)
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

    def callback(self, status: int) -> None:
        """Handle status updates from iAlarm-MK."""
        _LOGGER.debug("Received iAlarm-MK status: %s", status)
        self.hub.state = status
        # Schedule the update
        self.hass.async_create_task(self.async_update_data())

    async def async_update_data(self) -> None:
        """Update the data and notify about the new state."""
        _LOGGER.debug("Update the data in iAlarm-MK status: %s", self.hub.state)
        self.async_set_updated_data(self.hub.state)

    def _update_data(self) -> None:
        """Fetch data from iAlarm-MK via synchronous functions."""
        try:
            status: int = self.hub.ialarmmk.get_status()
            _LOGGER.debug("Updating internal state: %s", status)
            self.hub.state = status
        except ConnectionError as e:
            _LOGGER.error("Error fetching data from iAlarm-MK: %s", e)
            raise UpdateFailed("Connection error") from e

    async def _async_update_data(self) -> None:
        """Fetch data from iAlarm-MK 2."""
        _LOGGER.info("Fetching data.")
        tz = ZoneInfo(self.hass.config.time_zone)
        current_time = datetime.now(tz)

        try:
            async with timeout(15):
                await self.hass.async_add_executor_job(self._update_data)
                self.hub.ialarmmk.ialarmmkClient.login()

                attempts = 0
                max_attempts = 3

                while attempts < max_attempts:
                    try:
                        self.hub.ialarmmk.ialarmmkClient.login()
                        _LOGGER.debug("Login ok.")
                        status = self.hub.ialarmmk.ialarmmkClient.GetByWay()
                        _LOGGER.debug("Retrieve last sensors status.")
                        _LOGGER.debug("Status: %s", status)
                        break  # Se il blocco riesce, esci dal ciclo
                    except Exception as e:
                        _LOGGER.exception("Error during fetch data.")
                        self.hub.ialarmmk.ialarmmkClient.logout()
                        _LOGGER.info("After error, logout ok.")
                        attempts += 1
                        if attempts >= max_attempts:
                            _LOGGER.error("Failed after %d attempts", max_attempts)
                            raise UpdateFailed(e) from e
                        _LOGGER.info("Retrying... Attempt %d of %d", attempts + 1, max_attempts)

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
            raise UpdateFailed(error) from error
