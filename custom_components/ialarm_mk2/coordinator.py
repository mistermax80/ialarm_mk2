"""Coordinator."""

import asyncio
from asyncio.timeouts import timeout
from datetime import datetime, timedelta
import logging
import time
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .binary_sensor import IAlarmmkSensor
from .const import DOMAIN
from .hub import IAlarmMkHub

_LOGGER = logging.getLogger(__name__)


class iAlarmMk2Coordinator(DataUpdateCoordinator):
    """Class to manage fetching iAlarm-MK data."""

    def __init__(self, hass: HomeAssistant, hub: IAlarmMkHub) -> None:
        """Initialize global a data updater."""
        _LOGGER.info("Initialize global a data updater...")
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # update_interval=SCAN_INTERVAL,
            update_interval=timedelta(seconds=hub.scan_interval),
        )
        self.hub: IAlarmMkHub = hub
        self._subscription_task = None
        self.hub.ialarmmk.set_callback(self.callback, self.callback_only_status)
        # self.hub.ialarmmk.set_callback_only_status(self.callback_only_status)
        self.sensors: IAlarmmkSensor = []
        self.num_read_ok: int = 0
        self.num_read_ko: int = 0

    async def _async_setup(self):
        _LOGGER.info("Setup data updater...")

        SENSOR_CONFIG = []
        try:
            # Registrazione listener di spegnimento
            self.hass.bus.async_listen_once("homeassistant_stop", self.async_shutdown)
            # Start the subscription in the background
            if self.hub.ialarmmk.get_threads() < 1:
                self._subscription_task = asyncio.create_task(
                    self.hub.ialarmmk.subscribe()
                )
            _LOGGER.debug("Task: %s", self._subscription_task)
            # await self.hub.ialarmmk.subscribe()
            # self._subscription_task = asyncio.create_task(self.hub.ialarmmk.subscribe())
            # asyncio.run(self.hub.ialarmmk.subscribe())

            self.hub.ialarmmk.ialarmmkClient.login()
            _LOGGER.debug("Login OK.")
            idsSensors = self.hub.ialarmmk.ialarmmkClient.GetSensor()
            _LOGGER.debug("Retrieve sensors list OK.")
            zones = self.hub.ialarmmk.ialarmmkClient.GetZone()
            # _LOGGER.debug("Retrieve zones list OK. Zones: %s",zones)
            _LOGGER.debug("Retrieve zones list OK.")
            self.hub.ialarmmk.ialarmmkClient.logout()
            _LOGGER.debug("Logout OK.")

            for index, id_sensor in enumerate(idsSensors):
                if id_sensor:
                    sensor = {
                        "index": index,
                        "unique_id": id_sensor,
                        "entity_id": f"binary_sensor.{DOMAIN}_{zones[index].get('Name', 'no name')}",
                        "name": zones[index].get("Name", "no name"),
                        "zone_type": int(zones[index].get("Type", 0)),
                    }
                    SENSOR_CONFIG.append(sensor)

        except Exception:
            _LOGGER.exception("Error in setup entities.")
            self.hub.ialarmmk.ialarmmkClient.logout()
            _LOGGER.error("Logout OK.")
            raise

        for sc in SENSOR_CONFIG:
            iAlarmSensor = IAlarmmkSensor(
                self,
                self.hub.device_info,
                sc["name"],
                sc["index"],
                sc["entity_id"],
                sc["unique_id"],
                sc["zone_type"],
            )
            self.sensors.append(iAlarmSensor)

    def callback(self, event_data: dict) -> None:
        """Handle status updates from iAlarm-MK."""
        _LOGGER.debug("Received event from server, data: %s", event_data)

        _LOGGER.debug(
            "Old state: %s(%s)",
            self.hub.ialarmmk.status_dict.get(self.hub.state),
            self.hub.state,
        )
        status = event_data.get("Status")
        if status is not None:
            self.hub.state = status
        _LOGGER.debug(
            "New state: %s(%s)",
            self.hub.ialarmmk.status_dict.get(self.hub.state),
            self.hub.state,
        )

        lastRealUpdateStatus = event_data.get("LastRealUpdateStatus")
        if lastRealUpdateStatus is not None:
            self.hub.lastRealUpdateStatus = lastRealUpdateStatus

        # Evento personalizzato con nome "ialarm_mk_event"
        self.hass.bus.async_fire("ialarm_mk2_event", event_data)

        # Schedule the update
        self.hass.async_create_task(self.async_update_data())

    def callback_only_status(self, data_in: dict) -> None:
        """Handle status updates from alarm panel."""
        _LOGGER.debug("Received data in, data: %s", data_in)
        _LOGGER.debug(
            "Old state: %s(%s)",
            self.hub.ialarmmk.status_dict.get(self.hub.state),
            self.hub.state,
        )
        status = data_in.get("Status")
        if status is not None:
            self.hub.state = status
        _LOGGER.debug(
            "New state: %s(%s)", self.hub.ialarmmk.status_dict.get(status), status
        )

        lastRealUpdateStatus = data_in.get("LastRealUpdateStatus")
        if lastRealUpdateStatus is not None:
            self.hub.lastRealUpdateStatus = lastRealUpdateStatus

        user_id = data_in.get("user_id")
        self.hub.changed_by = user_id
        _LOGGER.debug("user_id: %s", user_id)
        """if user_id is not None:
            user_name = self.get_user_name(user_id)
            self.hub.changed_by = user_name if user_name else "Sconosciuto"
        """
        # Schedule the update
        self.hass.async_create_task(self.async_update_data())

    async def get_user_name(self, user_id):
        """get_user_name."""
        user = await self.hass.auth.async_get_user(user_id)
        if user:
            return user.name
        return None  # Se l'utente non esiste o non è trovato

    async def async_update_data(self) -> None:
        """Update the data and notify about the new state."""
        _LOGGER.debug(
            "Update the data status: %s(%s)",
            self.hub.ialarmmk.status_dict.get(self.hub.state),
            self.hub.state,
        )
        self.async_set_updated_data(self.hub.state)

    async def _async_update_data(self) -> None:
        """Fetch data from iAlarm-MK 2."""
        _LOGGER.info("Fetching data...")

        if not self.last_update_success:
            _LOGGER.warning("Last update was not successful, waiting 5 seconds.")
            await asyncio.sleep(10)

        try:
            async with timeout(30):
                await self.hass.async_add_executor_job(self._fetch_device_data)

            await self.async_update_data()
        except Exception as error:
            _LOGGER.exception("Error during fetch data.")
            raise UpdateFailed(error) from error

    def _fetch_device_data(self) -> None:
        """Fetch data from iAlarm-MK via synchronous functions."""
        try:
            status: int = self.hub.ialarmmk.get_status()
            _LOGGER.debug(
                "Updating internal state: %s(%s)",
                self.hub.ialarmmk.status_dict.get(status),
                status,
            )
            self.hub.state = status

            tz = ZoneInfo(self.hass.config.time_zone)
            current_time = datetime.now(tz)
            attempts = 0
            max_attempts = 3

            while attempts < max_attempts:
                try:
                    if self.num_read_ok > 1000:
                        _LOGGER.debug("Reset connection token.")
                        self.hub.ialarmmk.ialarmmkClient.logout()
                        self.num_read_ok = 0
                        self.num_read_ko = 0
                    self.hub.ialarmmk.ialarmmkClient.login()
                    _LOGGER.debug("Login ok.")
                    status = self.hub.ialarmmk.ialarmmkClient.GetByWay()
                    _LOGGER.debug("Retrieve last sensors status.")
                    _LOGGER.debug("Status: %s", status)
                    self.num_read_ok += 1

                    # Inizializza un messaggio di log e lo stato dei sensori
                    log_message = "\n"

                    for _idx, sensor in enumerate(self.sensors):
                        sensor: IAlarmmkSensor
                        state: int = status[int(sensor.index)]

                        log_message += f"\t- {sensor.name}: state {state} --> "

                        # Verifica se la zona è persa
                        if state & self.hub.ialarmmk.ZONE_LOSS:
                            sensor.set_attr_is_on(None)
                            log_message += f"(Persa) {bin(state)} \n"
                        # Verifica se la zona non è utilizzata
                        elif state == self.hub.ialarmmk.ZONE_NOT_USED:
                            sensor.set_attr_is_on(None)
                            log_message += f"(Non Usato) {bin(state)} \n"
                        # Verifica se la zona è in uso
                        elif state & self.hub.ialarmmk.ZONE_IN_USE:
                            # Verifica se la zona è in uso e in fault (aperto)
                            if state & self.hub.ialarmmk.ZONE_FAULT:
                                sensor.set_attr_is_on(True)
                                log_message += f"(Aperto) {bin(state)} \n"
                            # Verifica se la zona è in uso e non in fault (chiuso)
                            else:
                                sensor.set_attr_is_on(False)
                                log_message += f"(Chiuso) {bin(state)} \n"
                        else:
                            sensor.set_attr_is_on(None)
                            _LOGGER.warning(
                                "%s: state (Sconosciuto) %s \n", sensor.name, bin(state)
                            )

                        # Aggiorna gli attributi di stato extra
                        sensor.set_extra_state_attributes(
                            bool(state & self.hub.ialarmmk.ZONE_LOW_BATTERY),
                            bool(state & self.hub.ialarmmk.ZONE_LOSS),
                            bool(state & self.hub.ialarmmk.ZONE_BYPASS),
                            current_time,
                        )
                    # Logga il messaggio finale
                    _LOGGER.debug(log_message)

                    break  # Se il blocco riesce, esci dal ciclo
                except Exception as e:
                    self.num_read_ko += 1
                    _LOGGER.exception("Error during fetch data.")
                    self.hub.ialarmmk.ialarmmkClient.logout()
                    _LOGGER.info("After error, logout ok.")
                    attempts += 1
                    if attempts >= max_attempts:
                        _LOGGER.error("Failed after %d attempts", max_attempts)
                        raise UpdateFailed(e) from e
                    _LOGGER.info(
                        "Retrying... Attempt %d of %d in 5 seconds.",
                        attempts + 1,
                        max_attempts,
                    )
                    _LOGGER.debug("Waiting 5 second before next attempt.")
                    time.sleep(5)
                    _LOGGER.debug("Finished waiting, retrying now.")
                finally:
                    _LOGGER.debug(
                        "Numbers of update ok: %s, ko: %s",
                        self.num_read_ok,
                        self.num_read_ko,
                    )

        except ConnectionError as e:
            _LOGGER.error("Error fetching data: %s", e)
            raise UpdateFailed("Connection error") from e

    async def async_shutdown(self, *args):
        """Gestisci la chiusura delle risorse quando Home Assistant si spegne."""
        _LOGGER.info(
            "Shutting down iAlarmMk custom component, and close the connections active..."
        )
        if self._subscription_task:
            self._subscription_task.cancel()
            self.hub.ialarmmk.cancel_subscription()
            await self._subscription_task
        self.hub.ialarmmk.ialarmmkClient.logout()
        super().async_shutdown()
        _LOGGER.info("Shutdown iAlarmMk custom component completed.")
