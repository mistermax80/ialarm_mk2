"""Coordinator."""

import asyncio
from asyncio.timeouts import timeout
import copy
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
import random
import time
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, IALARMMK_P2P_PREFIX_TASK_NAME
from .hub import IAlarmMkHub
from .util import get_active_tasks

_LOGGER = logging.getLogger(__name__)


@dataclass
class SensorData:
    """Struttura dati dei sensori."""

    index: int
    unique_id: str
    zone_name: str
    zone_type: int
    state: int
    last_fetch_time: datetime
    last_battery_change_date: date
@dataclass
class AlarmData:
    """Struttura dati dell'allarme."""

    state: int | None = None
    temporary_state: str | None = None
    last_keeplive_ts: float = 0.0


@dataclass
class CoordinatorData:
    """Struttura dati compessiva per gesione del coordinator.data ."""

    alarm_data: AlarmData
    sensors_data: list[SensorData]


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
        self.hub.ialarmmk.set_callback(self.callback, self.callback_only_status)
        self._subscription_task = None

        # self.sensors: list[IAlarmmkSensor] = []
        # self.sensors_bat: list[IAlarmmkSensorBattery] = []
        # self.connectivity_sensor: list[IAlarmmkConnectivity] = []
        # Allarme inizializzato
        alarm_data = AlarmData()
        # Lista vuota di sensori, se ancora non disponibili
        sensors_data: list[SensorData] = []
        # Inizializzazione completa dell'oggetto Data
        self.data = CoordinatorData(alarm_data=alarm_data, sensors_data=sensors_data)

        self.num_read_ok: int = 0
        self.num_read_ko: int = 0

    async def _async_setup(self):
        _LOGGER.info("Setup data updater...")

        try:
            # Registrazione listener di spegnimento
            self.hass.bus.async_listen_once("homeassistant_stop", self.async_shutdown)

            # Start the subscription in the background
            tasks = get_active_tasks(IALARMMK_P2P_PREFIX_TASK_NAME + "SUBS")
            _LOGGER.debug(
                "Check if exist threads for '%s': %s",
                IALARMMK_P2P_PREFIX_TASK_NAME + "SUBS",
                len(tasks),
            )
            if len(tasks) < 1:
                task_name = f"{IALARMMK_P2P_PREFIX_TASK_NAME + 'SUBS'}_{random.randint(100, 999)}"
                self._subscription_task = asyncio.create_task(
                    self.hub.ialarmmk.subscribe(task_name), name=task_name
                )
                _LOGGER.debug("New Subscription Task: %s", self._subscription_task)
            else:
                _LOGGER.warning(
                    "Existing Subscription Task: %s", self._subscription_task
                )
                # TODO RECUPERARE IL THREAD E METTERLO IN _subscription_task OPPURE CHIUDERE IL PRECEDENTE E RIAPRIRLO NUOVO

            self.hub.ialarmmk.ialarmmkClient.login()
            _LOGGER.debug("Login OK.")
            idsSensors = self.hub.ialarmmk.ialarmmkClient.GetSensor()
            _LOGGER.debug("Retrieve sensors list OK.")
            zones = self.hub.ialarmmk.ialarmmkClient.GetZone()
            # _LOGGER.debug("Retrieve zones list OK. Zones: %s",zones)
            _LOGGER.debug("Retrieve zones list OK.")
            self.hub.ialarmmk.ialarmmkClient.logout()
            _LOGGER.debug("Logout OK.")

            alarm_data = AlarmData(0)
            sensors_data: list[SensorData] = []

            for index, id_sensor in enumerate(idsSensors):
                if id_sensor:
                    sensor = SensorData(
                        index,
                        id_sensor,
                        zones[index].get("Name", "Unamed"),
                        int(zones[index].get("Type", 0)),
                        0,
                        None,
                        self.config_entry.options.get(f'last_battery_change_{id_sensor}', None)
                    )
                    sensors_data.append(sensor)
            _LOGGER.debug("Sensors sensors_data: %s", sensors_data)
            self.data = CoordinatorData(alarm_data, sensors_data)

        except Exception:
            _LOGGER.exception("Error in setup entities.")
            self.hub.ialarmmk.ialarmmkClient.logout()
            _LOGGER.error("Logout OK.")
            raise

    def callback(self, event_data: dict) -> None:
        """Handle status updates from iAlarm-MK."""
        _LOGGER.debug("Manage event from server, data: %s", event_data)

        _LOGGER.debug(
            "Old state: %s(%s)",
            self.hub.ialarmmk.status_dict.get(self.data.alarm_data.state),
            self.data.alarm_data.state,
        )
        status = event_data.get("Status")
        if status is not None:
            self.data.alarm_data.state = status
        _LOGGER.debug(
            "New state: %s(%s)",
            self.hub.ialarmmk.status_dict.get(self.data.alarm_data.state),
            self.data.alarm_data.state,
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
        _LOGGER.debug("Manage manual update (only status), data: %s", data_in)

        _LOGGER.debug(
            "Old state: %s(%s)",
            self.hub.ialarmmk.status_dict.get(self.data.alarm_data.state),
            self.data.alarm_data.state,
        )
        status = data_in.get("Status")
        if status is not None:
            self.data.alarm_data.state = status
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
            self.hub.ialarmmk.status_dict.get(self.data.alarm_data.state),
            self.data.alarm_data.state,
        )
        return_data: CoordinatorData = self.data
        return_data.alarm_data.state = self.data.alarm_data.state
        _LOGGER.debug("return_data: %s", return_data)
        self.async_set_updated_data(return_data)

    async def _async_update_data(self) -> CoordinatorData:
        """Fetch data from iAlarm-MK 2."""
        _LOGGER.info("Fetching data...")

        if not self.last_update_success:
            _LOGGER.warning("Last update was not successful, waiting 5 seconds.")
            await asyncio.sleep(10)

        try:
            async with timeout(30):
                return await self.hass.async_add_executor_job(self._fetch_device_data)

            # await self.async_update_data()
        except Exception as error:
            _LOGGER.exception("Error during fetch data.")
            raise UpdateFailed(error) from error

    def _fetch_device_data(self) -> CoordinatorData:
        """Fetch data from iAlarm-MK via synchronous functions."""

        _LOGGER.debug("Coordinator data: %s", self.data)

        return_data = copy.deepcopy(self.data)

        try:
            return_data.alarm_data.last_keeplive_ts = (
                self.hub.ialarmmk.get_last_keeplive_ts()
            )
            status: int = self.hub.ialarmmk.get_status()
            _LOGGER.debug(
                "Updating internal state: %s(%s)",
                self.hub.ialarmmk.status_dict.get(status),
                status,
            )
            return_data.alarm_data.state = status

            tz = ZoneInfo(self.hass.config.time_zone)
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
                    log = ""
                    for _idx, sensor in enumerate(return_data.sensors_data):
                        sensor: SensorData
                        state: int = status[int(sensor.index)]
                        sensor.state = state
                        sensor.last_fetch_time = datetime.now(tz)

                        log += f"\n- {sensor.zone_name}, state:{state}"
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

        _LOGGER.debug(log)
        _LOGGER.debug("return_data: %s", return_data)

        return return_data

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
