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
from zoneinfo import ZoneInfo

from .pyialarmmk import iAlarmMkClient, iAlarmMkPushClient
import json
from homeassistant.core import HomeAssistant

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
        self.threadID = "iAlarmMK2-Thread"
        self.host = host
        self.port = port
        self.uid = uid
        self.pwd = pwd
        self.logger = logger

        self.ialarmmkClient = iAlarmMkClient(self.host, self.port, self.uid, self.pwd, self.logger)
        self.status = None
        self.callback = None
        self.callback_only_status = None
        self.hass: HomeAssistant = hass

        self._get_status()

    def set_callback(self, callback, callback_only_status):
        '''set_callback.'''
        self.callback = callback
        self.callback_only_status = callback_only_status
        
    async def subscribe(self):
        '''Fuzione migliorata.'''
        disconnect_time = 60 * 5

        while True:
            loop = asyncio.get_running_loop()
            on_con_lost = loop.create_future()
            try:
                transport, protocol = await loop.create_connection(
                    lambda: iAlarmMkPushClient(
                        self.host,
                        self.port,
                        self.uid,
                        self.set_status,
                        loop,
                        on_con_lost,
                        self.logger,
                    ),
                    self.host,
                    self.port,
                )
                self.logger.info("Connected to the server.")
                await asyncio.sleep(disconnect_time)

            except (ConnectionError, TimeoutError) as e:
                self.logger.error(f"Connection error: {e}")
                await asyncio.sleep(1)  # Attendi un secondo prima di ritentare

            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")

            finally:
                if transport:
                    transport.close()
                    self.logger.info("Transport closed.")
                await asyncio.sleep(1)  # Attendi un secondo prima di tentare di riconnettersi


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
            self.logger.debug("Callback is None")

    def cancel_alarm(self) -> None:
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(3)
            self._set_status(self.DISARMED)
            self.ialarmmkClient.logout()
        except Exception as e:
            self.logger.error("Error canceling alarm: %s", e)

    def arm_stay(self, user_id: str | None) -> None:
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(2)
            self._set_status(self.ARMED_STAY, user_id)
            self.ialarmmkClient.logout()
        except Exception as e:
            self.logger.error("Error arming alarm in stay mode: %s", e)

    def disarm(self, user_id: str | None) -> None:
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(1)
            self._set_status(self.DISARMED, user_id)
            self.ialarmmkClient.logout()
        except Exception as e:
            self.logger.error("Error disarming alarm: %s", e)

    def arm_away(self, user_id: str | None) -> None:
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(0)
            self._set_status(self.ALARM_ARMING, user_id)
            self.ialarmmkClient.logout()
        except Exception as e:
            self.logger.error("Error arming alarm in away mode: %s", e)

    def arm_partial(self, user_id: str | None) -> None:
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(8)
            self._set_status(self.ARMED_PARTIAL, user_id)
            self.ialarmmkClient.logout()
        except Exception as e:
            self.logger.error("Error arming alarm in partial mode: %s", e)

    def _set_status(self, status, user_id: str | None) -> None:
        if self.hass is not None:
            try:
                result = asyncio.run_coroutine_threadsafe(
                    self.async_set_status(status, user_id), self.hass.loop
                ).result()
                # Puoi anche loggare il risultato se necessario
                self.logger.debug("Status updated successfully: %s", status)
            except Exception as e:
                # Gestisci l'eccezione e logga l'errore
                self.logger.error("Error updating status: %s", e)

    async def async_set_status(self, status, user_id: str | None) -> None:
        tz = ZoneInfo(self.hass.config.time_zone)
        current_time = datetime.now(tz)
        data = {
            'Status': status,
            'LastRealUpdateStatus': current_time,
            'user_id': user_id
        }
        self.callback_only_status(data)

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
