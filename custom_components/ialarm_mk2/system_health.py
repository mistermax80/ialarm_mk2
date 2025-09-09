"""Provide info to system health."""

from typing import Any

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, IALARMMK_P2P_PREFIX_TASK_NAME
from .util import get_active_tasks


@callback
def async_register(
    hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    """Register system health callbacks."""
    register.async_register_info(system_health_info)


async def system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Get info for the info page."""
    # config_entry: ExampleConfigEntry = hass.config_entries.async_entries(DOMAIN)[0]
    # quota_info = await config_entry.runtime_data.async_get_quota_info()

    # ottieni il dict con tutti i config entry del dominio
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data:
        return {"error": "no coordinator found"}
    # prendi il primo coordinator (se hai più entry potresti dover scegliere)
    entry_id, coordinator = next(iter(domain_data.items()))
    return {
        "Number of data fetch ok:": coordinator.num_read_ok,
        "Number of data fetch ko:": coordinator.num_read_ko,
        "List of task:": get_active_tasks(IALARMMK_P2P_PREFIX_TASK_NAME),
    }
