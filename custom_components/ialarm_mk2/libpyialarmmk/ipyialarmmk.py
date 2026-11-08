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
import json
import logging
from datetime import datetime
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
    ALARM_DISARMING = 9
    UNAVAILABLE = 6
    ARMED_PARTIAL = 8

    status_dict = {
        ARMED_AWAY: "ARMED_AWAY",
        DISARMED: "DISARMED",
        ARMED_STAY: "ARMED_STAY",
        CANCEL: "CANCEL",
        TRIGGERED: "TRIGGERED",
        ALARM_ARMING: "ALARM_ARMING",
        ALARM_DISARMING: "ALARM_DISARMING",
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
        self.host = host
        self.port = port
        self.uid = uid
        self.pwd = pwd

        self.ialarmmkClient: iAlarmMkClient = iAlarmMkClient(
            self.host, self.port, self.uid, self.pwd
        )
        self.status = None
        self.callback = None
        self.callback_only_status = None
        self.hass: HomeAssistant = hass

        self.push_client: iAlarmMkPushClient | None = None
        self.keepalive_callback = None

        # self.transport = None
        self._cancelled = False

        self._get_status()

    def set_callback(self, callback, callback_only_status):
        """set_callback."""
        self.callback = callback
        self.callback_only_status = callback_only_status

    def set_keepalive_callback(self, callback):
        """Register callback for received keepalive messages."""
        self.keepalive_callback = callback

        if self.push_client is not None:
            self.push_client.keepalive_callback = callback

    async def subscribe(self, task_name: str):
        """Manage push subscription and reconnection."""

        retry_delay = 2
        connect_timeout = 15

        _LOGGER.info("[%s] Push subscription started.", task_name)

        try:
            while not self._cancelled:
                loop = asyncio.get_running_loop()
                on_con_lost = loop.create_future()
                client = None

                try:
                    client = iAlarmMkPushClient(
                        self.host,
                        self.port,
                        self.uid,
                        self.set_status,
                        loop,
                        on_con_lost,
                        keepalive_callback=self.keepalive_callback,
                    )

                    self.push_client = client

                    # Limit connection establishment time.
                    transport, _ = await asyncio.wait_for(
                        loop.create_connection(
                            lambda: client,
                            self.host,
                            self.port,
                        ),
                        timeout=connect_timeout,
                    )

                    client.transport = transport

                    _LOGGER.info(
                        "[%s] Push connection established.",
                        task_name,
                    )

                    # Wait for disconnection instead of sleeping.
                    await on_con_lost

                    _LOGGER.warning(
                        "[%s] Push connection lost.",
                        task_name,
                    )

                except asyncio.CancelledError:
                    _LOGGER.debug(
                        "[%s] Subscription cancelled.",
                        task_name,
                    )
                    raise

                except (OSError, ConnectionError, TimeoutError) as err:
                    _LOGGER.warning(
                        "[%s] Push connection error: %s",
                        task_name,
                        err,
                    )

                except Exception:
                    _LOGGER.exception(
                        "[%s] Unexpected push connection error.",
                        task_name,
                    )

                finally:
                    # Close only this connection's transport.
                    if client is not None:
                        client.handle_stop_connect()

                    if self.push_client is client:
                        self.push_client = None

                    if not on_con_lost.done():
                        on_con_lost.cancel()

                if not self._cancelled:
                    _LOGGER.info(
                        "[%s] Reconnecting push in %s seconds.",
                        task_name,
                        retry_delay,
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 30)

        except asyncio.CancelledError:
            _LOGGER.debug(
                "[%s] Subscription task stopped.",
                task_name,
            )
            raise

        finally:
            _LOGGER.info(
                "[%s] Push subscription terminated.",
                task_name,
            )

    def cancel_subscription(self):
        """Stop push subscription and keepalive."""
        self._cancelled = True

        if self.push_client is not None:
            self.push_client.handle_stop_connect()
            self.push_client = None

        _LOGGER.debug("Push subscription cancellation requested.")

    def get_last_keeplive_ts(self):
        """Metodo per prendere l'ultimo timestamp ricevuto per il messaggio di keeplive."""
        if self.push_client is None:
            return None
        return self.push_client.last_keeplive_ts

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
            "Real status received is: %s(%s)",
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
            _LOGGER.debug("Callback is None.")

    def reboot(self):
        """Send reboot command to iAlarm-MK panel."""
        _LOGGER.info("Sending reboot command to iAlarm-MK.")

        # Dedicated client to avoid interfering with polling.
        client = iAlarmMkClient(
            self.host,
            self.port,
            self.uid,
            self.pwd,
        )

        try:
            client.login()
            response = client.Reset(True)

            _LOGGER.info(
                "iAlarm-MK reboot command response: %s",
                response,
            )

            if response is None:
                _LOGGER.warning(
                    "Reboot response missing; command may have been executed."
                )
            elif isinstance(response, dict) and response.get("Err"):
                raise RuntimeError(f"Reboot rejected: {response['Err']}")

        finally:
            client.logout()

    def cancel_alarm(self, user_id: str | None) -> None:
        """Command for cancel alarm."""
        try:
            self.ialarmmkClient.login()
            self.ialarmmkClient.SetAlarmStatus(self.CANCEL)
            self._set_status(self.DISARMED, user_id)
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
            self._set_status(self.ALARM_DISARMING, user_id)
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
            self._set_status(self.ALARM_ARMING, user_id)
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
