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

        self.callback = None
        self.hass = hass

        self._get_status()

    def set_callback(self, callback):
        '''set_callback.'''
        self.callback = callback

    async def subscribe(self):
        disconnect_time = 60 * 5
        while True:
            loop = asyncio.get_running_loop()
            on_con_lost = loop.create_future()
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

            try:
                await asyncio.sleep(disconnect_time)
            except Exception as e:
                self.logger.debug(e)
                pass
            finally:
                transport.close()
                transport = None
                await asyncio.sleep(1)

    def _get_status(self):
        try:
            self.ialarmmkClient.login()
            self.status = self.ialarmmkClient.GetAlarmStatus().get("DevStatus")
            self.ialarmmkClient.logout()
        except:
            self.status = self.UNAVAILABLE
            pass

    def get_status(self):
        return self.status

    def set_status(self, status):
        new_status = int(status.get("Cid"))

        if new_status == 1401:
            self.status = 1
        elif new_status == 1406:
            self.status = 1
        elif new_status == 3401:
            self.status = 0
        elif new_status == 3441:
            self.status = 2
        elif new_status == 1100 or new_status == 1101 or new_status == 1120:
            self.status = 4
        elif new_status == 1131 or new_status == 1132 or new_status == 1133:
            self.status = 4
        elif new_status == 1134 or new_status == 1137:
            self.status = 4

        if self.callback is not None:
            self.callback(self.status)

    def cancel_alarm(self) -> None:
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(3)
            self._set_status(self.DISARMED)
            self.ialarmmkClient.logout()
        except:
            pass

    def arm_stay(self) -> None:
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(2)
            self._set_status(self.ARMED_STAY)
            self.ialarmmkClient.logout()
        except:
            pass

    def disarm(self) -> None:
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(1)
            self._set_status(self.DISARMED)
            self.ialarmmkClient.logout()
        except:
            pass

    def arm_away(self) -> None:
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(0)
            self._set_status(self.ALARM_ARMING)
            self.ialarmmkClient.logout()
        except:
            pass

    def _set_status(self, status):
        if self.hass is not None:
            asyncio.run_coroutine_threadsafe(
                self.async_set_status(status), self.hass.loop
            ).result()

    async def async_set_status(self, status):
        self.callback(status)
        pass

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
