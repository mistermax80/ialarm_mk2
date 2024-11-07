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

    status_dict = {
        ARMED_AWAY: "ARMED_AWAY",
        DISARMED: "DISARMED",
        ARMED_STAY: "ARMED_STAY",
        CANCEL: "CANCEL",
        TRIGGERED: "TRIGGERED",
        ALARM_ARMING: "ALARM_ARMING",
        UNAVAILABLE: "UNAVAILABLE"
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
        hass=None,
        logger=None,
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
        self.subscribed_task = None
        self.callback = None
        self.hass = hass

        self._get_status()

    def set_callback(self, callback):
        '''set_callback.'''
        self.callback = callback

    async def subscribe(self):
        '''Funzione principale per mantenere la connessione.'''
        disconnect_time = 60 * 5  # 5 minuti
        self.subscribed_task = asyncio.create_task(self._maintain_connection(disconnect_time))
        self.logger.debug("Task created: %s", self.subscribed_task)

    async def _maintain_connection(self, disconnect_time):
        '''Gestisce la connessione e la disconnessione periodica.'''
        transport = None
        try:
            while True:
                transport, protocol = await self._connect()
                self.logger.info("Connected to the server.")
                await asyncio.sleep(disconnect_time)  # Timeout di disconnessione
        except asyncio.CancelledError:
            await self._handle_task_cancellation(transport)
        except Exception as e:
            await self._handle_unexpected_error(e, transport)
        finally:
            if transport:
                transport.close()
                self.logger.info("Transport closed.")

    async def _connect(self):
        '''Crea una nuova connessione.'''
        on_con_lost = asyncio.get_running_loop().create_future()
        return await asyncio.get_running_loop().create_connection(
            lambda: iAlarmMkPushClient(
                self.host,
                self.port,
                self.uid,
                self.set_status,
                asyncio.get_running_loop(),
                on_con_lost,
                self.logger,
            ),
            self.host,
            self.port,
        )

    async def _handle_task_cancellation(self, transport):
        '''Gestisce la cancellazione del task.'''
        self.logger.info("Subscription task was cancelled.")
        if transport:
            transport.close()

    async def _handle_unexpected_error(self, error, transport):
        '''Gestisce errori imprevisti durante la connessione.'''
        self.logger.error(f"Unexpected error: {error}")
        if transport:
            transport.close()

    def cancel_subscription(self):
        '''Cancella il task di sottoscrizione per evitare thread demoniaci.'''
        if self.subscribed_task:
            self.subscribed_task.cancel()
            self.logger.info("Subscription task cancelled.")

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
            1134: 4, 1137: 4
        }

        event_data = {
            "Name": data_event_received.get("Name"),
            "Aid": data_event_received.get("Aid"),
            "Cid": cid,
            "Status": status_map.get(cid, data_event_received.get("status")),
            "Content": data_event_received.get("Content"),
            "ZoneName": data_event_received.get("ZoneName"),
            "Zone": data_event_received.get("Zone"),
            "Err": data_event_received.get("Err"),
        }

        # Invoca il callback se definito
        if self.callback:
            self.logger.debug("Invoke callback to passing event data: %s", event_data)
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

    def arm_stay(self) -> None:
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(2)
            self._set_status(self.ARMED_STAY)
            self.ialarmmkClient.logout()
        except Exception as e:
            self.logger.error("Error arming alarm in stay mode: %s", e)

    def disarm(self) -> None:
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(1)
            self._set_status(self.DISARMED)
            self.ialarmmkClient.logout()
        except Exception as e:
            self.logger.error("Error disarming alarm: %s", e)

    def arm_away(self) -> None:
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(0)
            self._set_status(self.ALARM_ARMING)
            self.ialarmmkClient.logout()
        except Exception as e:
            self.logger.error("Error arming alarm in away mode: %s", e)

    def _set_status(self, status):
        if self.hass is not None:
            try:
                result = asyncio.run_coroutine_threadsafe(
                    self.async_set_status(status), self.hass.loop
                ).result()
                # Puoi anche loggare il risultato se necessario
                self.logger.debug("Status updated successfully: %s", status)
            except Exception as e:
                # Gestisci l'eccezione e logga l'errore
                self.logger.error("Error updating status: %s", e)

    async def async_set_status(self, status):
        self.callback(status)

    def get_mac(self) -> str:
        self.ialarmmkClient.login()
        network_info = self.ialarmmkClient.GetNet()
        self.ialarmmkClient.logout()
        if network_info is not None:
            mac = network_info.get("Mac", "")
        if mac:
            return mac
        raise ConnectionError(
            "An error occurred trying to connect to the alarm "
            "system or received an unexpected reply"
        )
