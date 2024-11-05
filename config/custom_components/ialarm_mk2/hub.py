'''Hub per la utilizzo della libreria.'''
import logging

from homeassistant.helpers.device_registry import format_mac

from . import libpyialarmmk as ipyialarmmk

_LOGGER = logging.getLogger(__name__)

class IAlarmMkHub:
    """IAlarmMkHub."""

    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        """Initialize."""
        _LOGGER.info("Initialize IAlarmMkHub")
        self.host: str = host
        self.port: int = port
        self.username: str = username
        self.password: str = password
        self.mac: str = None
        self.ialarmmk = ipyialarmmk.iAlarmMkInterface(self.username, self.password, self.host, self.port, None, _LOGGER)

    async def get_mac(self) -> str:
        """Test if we can authenticate with the host."""
        _LOGGER.debug("IAlarmMkHub.get_mac")
        if self.mac is None:
            self.mac = format_mac(self.ialarmmk.get_mac())
        _LOGGER.debug("MAC: %s", self.mac)
        return self.mac

    async def validate(self) -> bool:
        """Test if we can authenticate with the host."""
        _LOGGER.debug("IAlarmMkHub.validate")
        await self.get_mac()
        return True