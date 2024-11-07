'''Hub per utilizzo liberia.'''
import logging

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import DeviceInfo

from . import libpyialarmmk as ipyialarmmk

_LOGGER = logging.getLogger(__name__)

class IAlarmMkHub:
    """Gestisce la connessione con iAlarm-MK."""

    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        """Inizializza la connessione con iAlarm-MK."""
        _LOGGER.info("Initializing iAlarmMkHub")
        self.host: str = host
        self.port: int = port
        self.username: str = username
        self.password: str = password
        self.mac: str = None
        self.state: int = None
        self.ialarmmk = ipyialarmmk.iAlarmMkInterface(self.username, self.password, self.host, self.port, None, _LOGGER)
        self.device_info = None

    async def validate(self) -> bool:
        """Verifica la connessione e recupera le informazioni sul dispositivo."""
        _LOGGER.info("Validating connection, getting MAC address...")

        try:
            # Verifica se l'indirizzo MAC è già stato recuperato
            if self.mac is None:
                # Recupera l'indirizzo MAC e imposta le informazioni sul dispositivo
                self.mac = format_mac(self.ialarmmk.get_mac())
                _LOGGER.info("MAC address: %s", self.mac)

                # Imposta le informazioni sul dispositivo
                self.device_info = DeviceInfo(
                    manufacturer="antifurto 365",
                    name="iAlarm-MK",
                    connections={(dr.CONNECTION_NETWORK_MAC, self.mac)}
                )
        except Exception as e:
            _LOGGER.error("Failed to validate connection or get MAC address: %s", e)
            return False  # Restituisce False in caso di errore
        return True  # Connessione riuscita
