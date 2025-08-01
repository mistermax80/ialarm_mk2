"""Hub per l'utilizzo della libreria iAlarmMk."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import DeviceInfo

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
        self.state: int = None
        self.changed_by: str = None
        self.lastRealUpdateStatus = None
        self.ialarmmk = ipyialarmmk.iAlarmMkInterface(
            self.username, self.password, self.host, self.port, self.hass, _LOGGER
        )
        self.device_info: DeviceInfo | None = None

    async def validate(self) -> bool:
        """Verifica la connessione e recupera le informazioni sul dispositivo."""
        _LOGGER.info("Validating connection, getting MAC address...")

        try:
            # Verifica se l'indirizzo MAC è già stato recuperato
            if self.mac is None:
                # Recupera l'indirizzo MAC e imposta le informazioni sul dispositivo
                data_in: dict[str, str] = self.ialarmmk.get_mac()
                self.mac = format_mac(data_in.get("Mac"))
                self.name = data_in.get("Name")
                _LOGGER.info("MAC address: %s", self.mac)

                # Imposta le informazioni sul dispositivo
                self.device_info = DeviceInfo(
                    manufacturer="antifurto 365",
                    name=self.name,
                    connections={(dr.CONNECTION_NETWORK_MAC, self.mac)},
                )
        except Exception:
            _LOGGER.exception("Error during validation IAlarm device.")
            return False

        return True  # Connessione riuscita
