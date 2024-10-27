"""iAlarmMK utils."""
import logging

from homeassistant import core
from homeassistant.helpers.device_registry import format_mac

from . import libpyialarmmk as ipyialarmmk

_LOGGER = logging.getLogger(__name__)


async def async_get_ialarmmk_mac(
    hass: core.HomeAssistant, ialarmmk: ipyialarmmk.iAlarmMkInterface
) -> str:
    """Retrieve iAlarm-MK MAC address."""
    _LOGGER.debug("Retrieving ialarm-MK mac address")

    mac = await hass.async_add_executor_job(ialarmmk.get_mac)

    return format_mac(mac)
