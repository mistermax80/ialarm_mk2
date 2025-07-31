# Copyright (C) 2022, ServiceA3
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import asyncio
from datetime import datetime
import json
import threading
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant

from .pyialarmmk import iAlarmMkClient, iAlarmMkPushClient


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
        ARMED_PARTIAL: "ARMED_PARTIAL"
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
        logger = None,
    ):
        '''Impostazione.'''
        self.threadID = "iAlarmMK2-ThreadID"
        self.host = host
        self.port = port
        self.uid = uid
        self.pwd = pwd
        self.logger = logger

        self.ialarmmkClient = iAlarmMkClient(self.host, self.port, self.uid, self.pwd, self.logger)
        self.status = None
        self.callback = None
        self.hass: HomeAssistant = hass

        self.client = None
        self.transport = None
        self._cancelled = False

        self._get_status()

    def set_callback(self, callback):
        '''set_callback.'''
        self.callback = callback

    def get_threads(self) -> int:
        '''Recupera il numero di threads attivi.'''
        threads = threading.enumerate()
        specific_threads = [t for t in threads if t.name.startswith(self.threadID)]
        for thread in specific_threads:
            self.logger.debug(f"Active thread: {thread.name}")  # noqa: G004
        return len(specific_threads)

    async def subscribe(self):
        '''Funzione migliorata.'''
        disconnect_time = 60 * 5

        while True:
            # Controlla se il task è stato cancellato prima di eseguire altre operazioni
            if self._cancelled:
                self.logger.info("Subscription task cancellato.")
                break

            num_treads = self.get_threads()
            self.logger.debug(f"Numbers of threads for '{self.threadID}': {num_treads}")  # noqa: G004
            loop = asyncio.get_running_loop()
            on_con_lost = loop.create_future()

            try:
                # Se non esiste un client o il trasporto è chiuso, crea una nuova connessione
                if self.client is None or self.transport is None or self.transport.is_closing():
                    if self.transport:
                        self.logger.debug("Closing existing transport.")
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
                        self.logger,
                    )
                    self.transport, protocol = await loop.create_connection(
                        lambda: self.client,
                        self.host,
                        self.port,
                    )
                    self.logger.info("Connected to the server.")

                # Mantieni la connessione per `disconnect_time`
                await asyncio.sleep(disconnect_time)

            except (ConnectionError, TimeoutError) as e:
                self.logger.error(f"Connection error: {e}")

            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")

            finally:
                # Chiudi il trasporto se il client segnala che la connessione è terminata
                if on_con_lost.done():
                    self.logger.info("Connection lost. Cleaning up...")
                    if self.transport and not self.transport.is_closing():
                        self.transport.close()
                    self.client = None  # Resetta il client
                    self.transport = None  # Resetta il trasporto

                # Attendi prima di riconnetterti
                await asyncio.sleep(1)

    def cancel_subscription(self):
        '''Metodo per cancellare la subscription.'''
        self._cancelled = True  # Imposta il flag di cancellazione

    def _get_status(self):
        self.logger.debug("Retrieving DevStatus...")
        try:
            self.ialarmmkClient.login()
            self.status = self.ialarmmkClient.GetAlarmStatus().get("DevStatus")
            self.logger.debug("DevStatus: %s(%s)", self.status_dict.get(self.status),self.status)
            self.ialarmmkClient.logout()
        except Exception:
            self.status = self.UNAVAILABLE

    def get_status(self):
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
            1100: 4, 1101: 4, 1120: 4,
            1131: 4, 1132: 4, 1133: 4,
            1134: 4, 1137: 4,
            3456: 8
        }

        self.status = status_map.get(cid, data_event_received.get("status",self.status))
        self.logger.debug("Real status updated to: %s(%s)", self.status_dict.get(self.status),self.status)

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
            "Json": json.dumps(data_event_received)
        }

        # Invoca il callback se definito
        if self.callback:
            #self.logger.debug("Invoke callback to passing event data: %s", event_data)
            self.callback(event_data)
        else:
            self.logger.warning("Callback is None")

    def cancel_alarm(self) -> None:
        try:
            self.ialarmmkClient.login()
            ret_value = self.ialarmmkClient.SetAlarmStatus(self.CANCEL)
            self.logger.debug("Return value: %s", ret_value)
            #self._set_status(self.DISARMED)
            self.ialarmmkClient.logout()
        except Exception as e:
            self.logger.error("Error canceling alarm: %s", e)

    def arm_stay(self, user_id: str | None) -> None:
        try:
            self.ialarmmkClient.login()
            ret_value = self.ialarmmkClient.SetAlarmStatus(self.ARMED_STAY)
            self.logger.debug("Return value: %s", ret_value)
            #self._set_status(self.ARMED_STAY, user_id)
            self.ialarmmkClient.logout()
        except Exception as e:
            self.logger.error("Error arming alarm in stay mode: %s", e)

    def disarm(self, user_id: str | None) -> None:
        try:
            self.ialarmmkClient.login()
            ret_value = self.ialarmmkClient.SetAlarmStatus(self.DISARMED)
            self.logger.debug("Return value: %s", ret_value)
            #self._set_status(self.DISARMED, user_id)
            self.ialarmmkClient.logout()
        except Exception as e:
            self.logger.error("Error disarming alarm: %s", e)

    def arm_away(self, user_id: str | None) -> None:
        try:
            self.ialarmmkClient.login()
            ret_value = self.ialarmmkClient.SetAlarmStatus(self.ARMED_AWAY)
            self.logger.debug("Return value: %s", ret_value)
            #self._set_status(self.ALARM_ARMING, user_id)
            self.ialarmmkClient.logout()
        except Exception as e:
            self.logger.error("Error arming alarm in away mode: %s", e)

    def arm_partial(self, user_id: str | None) -> None:
        try:
            self.ialarmmkClient.login()
            ret_value = self.ialarmmkClient.SetAlarmStatus(self.ARMED_PARTIAL)
            self.logger.debug("Return value: %s", ret_value)
            #self._set_status(self.ARMED_PARTIAL, user_id)
            self.ialarmmkClient.logout()
        except Exception as e:
            self.logger.error("Error arming alarm in partial mode: %s", e)

    def get_mac(self) -> dict:
        self.ialarmmkClient.login()
        network_info = self.ialarmmkClient.GetNet()
        self.ialarmmkClient.logout()
        if network_info is not None:
            mac = network_info.get("Mac", "")
            name = network_info.get("Name", "iAlarm-MK")
            return_data = {
                'Mac': mac,
                'Name': name
        }
        if mac:
            return return_data
        raise ConnectionError(
            "An error occurred trying to connect to the alarm "
            "system or received an unexpected reply"
        )
