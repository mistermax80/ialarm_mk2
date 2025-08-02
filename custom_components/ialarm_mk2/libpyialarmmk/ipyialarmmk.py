"""Copyright (C) 2022, ServiceA3.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import asyncio
from datetime import datetime
import json
import logging
import threading
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant

from .pyialarmmk import iAlarmMkClient, iAlarmMkPushClient

_LOGGER = logging.getLogger(__name__)


class iAlarmMkInterface:
    """Interface with pyialarmmk library."""

    ARMED_AWAY = 0
    DISARMED = 1
    ARMED_STAY = 2
    CANCEL = 3
    TRIGGERED = 4
    ALARM_ARMING = 5
    UNAVAILABLE = 6
    ARMED_PARTIAL = 8

    status_dict = {
        ARMED_AWAY: "ARMED_AWAY",
        DISARMED: "DISARMED",
        ARMED_STAY: "ARMED_STAY",
        CANCEL: "CANCEL",
        TRIGGERED: "TRIGGERED",
        ALARM_ARMING: "ALARM_ARMING",
        UNAVAILABLE: "UNAVAILABLE",
        ARMED_PARTIAL: "ARMED_PARTIAL",
    }

    ZONE_NOT_USED = 0
    ZONE_IN_USE = 1 << 0
    ZONE_ALARM = 1 << 1
    ZONE_BYPASS = 1 << 2
    ZONE_FAULT = 1 << 3
    ZONE_LOW_BATTERY = 1 << 4
    ZONE_LOSS = 1 << 5

    IALARMMK_P2P_DEFAULT_PORT = 18034
    IALARMMK_P2P_DEFAULT_HOST = "47.91.74.102"

    def __init__(
        self,
        uid: str,
        pwd: str,
        host: str,
        port: int,
        hass: HomeAssistant = None,
        logger=None,
    ):
        """Impostazione."""
        self.threadID = "iAlarmMK2-ThreadID"
        self.host = host
        self.port = port
        self.uid = uid
        self.pwd = pwd

        self.ialarmmkClient = iAlarmMkClient(self.host, self.port, self.uid, self.pwd)
        self.status = None
        self.callback = None
        self.callback_only_status = None
        self.hass: HomeAssistant = hass

        self.client = None
        self.transport = None
        self._cancelled = False

        self._get_status()

    def set_callback(self, callback, callback_only_status):
        """set_callback."""
        self.callback = callback
        self.callback_only_status = callback_only_status

    def get_threads(self) -> int:
        """Recupera il numero di threads attivi."""
        threads = threading.enumerate()
        specific_threads = [t for t in threads if t.name.startswith(self.threadID)]
        for thread in specific_threads:
            _LOGGER.debug(f"Active thread: {thread.name}")  # noqa: G004
        return len(specific_threads)

    async def subscribe(self):
        """Funzione migliorata."""
        disconnect_time = 60 * 5

        while True:
            # Controlla se il task è stato cancellato prima di eseguire altre operazioni
            if self._cancelled:
                _LOGGER.info("Subscription task cancelled.")
                break

            num_treads = self.get_threads()
            _LOGGER.debug(f"Numbers of threads for '{self.threadID}': {num_treads}")  # noqa: G004
            loop = asyncio.get_running_loop()
            on_con_lost = loop.create_future()

            try:
                # Se non esiste un client o il trasporto è chiuso, crea una nuova connessione
                if (
                    self.client is None
                    or self.transport is None
                    or self.transport.is_closing()
                ):
                    if self.transport:
                        _LOGGER.debug("Closing existing transport.")
                        self.transport.close()
                        self.transport = None  # Resetta il trasporto

                    self.client = iAlarmMkPushClient(
                        self.host,
                        self.port,
                        self.uid,
                        self.set_status,
                        loop,
                        on_con_lost,
                        self.threadID,
                    )
                    self.transport, protocol = await loop.create_connection(
                        lambda: self.client,
                        self.host,
                        self.port,
                    )
                    _LOGGER.info("Connected to the server.")

                # Mantieni la connessione per `disconnect_time`
                await asyncio.sleep(disconnect_time)

            except (ConnectionError, TimeoutError) as e:
                _LOGGER.error("Connection error: %s", e)

            except Exception as e:
                _LOGGER.error("Unexpected error:  %s", e)

            finally:
                # Chiudi il trasporto se il client segnala che la connessione è terminata
                if on_con_lost.done():
                    _LOGGER.info("Connection lost. Cleaning up...")
                    if self.transport and not self.transport.is_closing():
                        self.transport.close()
                    self.client = None  # Resetta il client
                    self.transport = None  # Resetta il trasporto

                # Attendi prima di riconnetterti
                await asyncio.sleep(1)

    def cancel_subscription(self):
        """Metodo per cancellare la subscription."""
        self._cancelled = True  # Imposta il flag di cancellazione

    def _get_status(self):
        _LOGGER.debug("Retrieving DevStatus...")
        try:
            self.ialarmmkClient.login()
            self.status = self.ialarmmkClient.GetAlarmStatus().get("DevStatus")
            _LOGGER.debug(
                "DevStatus: %s(%s)", self.status_dict.get(self.status), self.status
            )
            self.ialarmmkClient.logout()
        except Exception:
            self.status = self.UNAVAILABLE

    def get_status(self):
        """Return value local variable."""
        return self.status

    def set_status(self, data_event_received):
        """Recupera i dati dell'evento ed imposta lo stato dell'allarme."""
        # Ottieni il nuovo stato
        cid = int(data_event_received.get("Cid"))
        # Mappatura degli stati
        status_map = {
            1401: 1,
            1406: 1,
            3401: 0,
            3441: 2,
            1100: 4,
            1101: 4,
            1120: 4,
            1131: 4,
            1132: 4,
            1133: 4,
            1134: 4,
            1137: 4,
            3456: 8,
        }

        self.status = status_map.get(
            cid, data_event_received.get("status", self.status)
        )
        _LOGGER.debug(
            "Real status updated to: %s(%s)",
            self.status_dict.get(self.status),
            self.status,
        )

        tz = ZoneInfo(self.hass.config.time_zone)
        current_time = datetime.now(tz)

        event_data = {
            "Name": data_event_received.get("Name"),
            "Aid": data_event_received.get("Aid"),
            "Cid": cid,
            "Status": self.status,
            "LastRealUpdateStatus": current_time,
            "Content": data_event_received.get("Content"),
            "ZoneName": data_event_received.get("ZoneName"),
            "Zone": data_event_received.get("Zone"),
            "Err": data_event_received.get("Err"),
            "Json": json.dumps(data_event_received),
        }

        # Invoca il callback se definito
        if self.callback:
            # _LOGGER.debug("Invoke callback to passing event data: %s", event_data)
            self.callback(event_data)
        else:
            _LOGGER.debug("Callback is None")

    def cancel_alarm(self) -> None:
        """Command for cancel alarm."""
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(self.CANCEL)
            self._set_status(self.DISARMED)
            self.ialarmmkClient.logout()
        except Exception as e:
            _LOGGER.error("Error canceling alarm: %s", e)

    def arm_stay(self, user_id: str | None) -> None:
        """Command for arm alarm."""
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(self.ARMED_STAY)
            self._set_status(self.ARMED_STAY, user_id)
            self.ialarmmkClient.logout()
        except Exception as e:
            _LOGGER.error("Error arming alarm in stay mode: %s", e)

    def disarm(self, user_id: str | None) -> None:
        """Command for disarm alarm."""
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(self.DISARMED)
            self._set_status(self.DISARMED, user_id)
            self.ialarmmkClient.logout()
        except Exception as e:
            _LOGGER.error("Error disarming alarm: %s", e)

    def arm_away(self, user_id: str | None) -> None:
        """Command for arm alarm."""
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(self.ARMED_AWAY)
            self._set_status(self.ALARM_ARMING, user_id)
            self.ialarmmkClient.logout()
        except Exception as e:
            _LOGGER.error("Error arming alarm in away mode: %s", e)

    def arm_partial(self, user_id: str | None) -> None:
        """Command for arm partial alarm."""
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(self.ARMED_PARTIAL)
            self._set_status(self.ARMED_PARTIAL, user_id)
            self.ialarmmkClient.logout()
        except Exception as e:
            _LOGGER.error("Error arming alarm in partial mode: %s", e)

    def _set_status(self, status, user_id: str | None) -> None:
        if self.hass is not None:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.async_set_status(status, user_id), self.hass.loop
                ).result()
                # Puoi anche loggare il risultato se necessario
                _LOGGER.debug("Status updated successfully: %s", status)
            except Exception as e:
                # Gestisci l'eccezione e logga l'errore
                _LOGGER.error("Error updating status: %s", e)

    async def async_set_status(self, status, user_id: str | None) -> None:
        """Set internal data and call callback for update status."""
        tz = ZoneInfo(self.hass.config.time_zone)
        current_time = datetime.now(tz)
        data = {
            "Status": status,
            "LastRealUpdateStatus": current_time,
            "user_id": user_id,
        }
        self.callback_only_status(data)

    def get_mac(self) -> dict:
        """For retrieve MAC address."""
        self.ialarmmkClient.login()
        network_info = self.ialarmmkClient.GetNet()
        self.ialarmmkClient.logout()
        if network_info is not None:
            mac = network_info.get("Mac", "")
            name = network_info.get("Name", "iAlarm-MK")
            return_data = {"Mac": mac, "Name": name}
        if mac:
            return return_data
        raise ConnectionError(
            "An error occurred trying to connect to the alarm "
            "system or received an unexpected reply"
        )
