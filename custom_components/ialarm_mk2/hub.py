"""Hub per l'utilizzo della libreria iAlarmMk."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac

from . import libpyialarmmk as ipyialarmmk

_LOGGER = logging.getLogger(__name__)


class IAlarmMkHub:
    """Gestisce la connessione con iAlarm-MK."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        username: str,
        password: str,
        scan_interval: int,
    ) -> None:
        """Inizializza la connessione con iAlarm-MK."""
        _LOGGER.info("Initializing iAlarmMkHub")
        self.hass: HomeAssistant = hass
        self.host: str = host
        self.port: int = port
        self.username: str = username
        self.password: str = password
        self.scan_interval: int = scan_interval
        self.mac: str = None
        self.name: str = None
        # self.state: int = None
        self.changed_by: str = None
        self.lastRealUpdateStatus = None
        self.ialarmmk = ipyialarmmk.iAlarmMkInterface(
            self.username, self.password, self.host, self.port, self.hass
        )

    async def validate(self) -> bool:
        """Verifica la connessione e recupera le informazioni del dispositivo."""
        _LOGGER.info("Validating connection, getting MAC address...")

        try:
            if self.mac is None:
                data_in = await self.hass.async_add_executor_job(self.ialarmmk.get_mac)

                self.mac = format_mac(data_in["Mac"])
                self.name = data_in.get("Name", "iAlarm-MK")

                _LOGGER.info("MAC address: %s", self.mac)

        except Exception:
            _LOGGER.exception("Error during iAlarm device validation.")
            return False

        return True
