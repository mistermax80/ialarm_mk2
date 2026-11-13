"""Button entities for iAlarm-MK."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import iAlarmMk2Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up reboot button."""

    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([IAlarmMkRebootButton(coordinator)])


class IAlarmMkRebootButton(
    CoordinatorEntity[iAlarmMk2Coordinator],
    ButtonEntity,
):
    """Reboot the iAlarm-MK control panel."""

    _attr_has_entity_name = True
    _attr_translation_key = "reboot"
    _attr_icon = "mdi:restart"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator):
        """Initialize the reboot button."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{coordinator.hub.username}_reboot"

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.hub.username)},
        }

    async def async_press(self) -> None:
        """Send the reboot command to the control panel."""

        alarm = self.coordinator.hub.ialarmmk
        state = self.coordinator.data.alarm_data.state

        # Reboot is allowed only when the alarm is disarmed.
        if state != alarm.DISARMED:
            raise HomeAssistantError(
                "The control panel must be disarmed before rebooting."
            )

        _LOGGER.warning("Manual reboot requested for iAlarm-MK control panel.")

        try:
            await self.hass.async_add_executor_job(alarm.reboot)

        except Exception as err:
            _LOGGER.exception("Failed to send reboot command to iAlarm-MK.")
            raise HomeAssistantError(
                "Unable to confirm the control panel reboot command."
            ) from err
