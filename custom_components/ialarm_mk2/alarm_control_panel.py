"""Interfaces with iAlarmMk control panels."""

from __future__ import annotations

import logging
from collections.abc import Callable

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import libpyialarmmk as ipyialarmmk
from .const import DOMAIN
from .coordinator import iAlarmMk2Coordinator
from .libpyialarmmk.ipyialarmmk import AlarmCommandError

_LOGGER = logging.getLogger(__name__)

IALARMMK_TO_HASS = {
    ipyialarmmk.iAlarmMkInterface.ARMED_AWAY: AlarmControlPanelState.ARMED_AWAY,
    ipyialarmmk.iAlarmMkInterface.ARMED_STAY: AlarmControlPanelState.ARMED_HOME,
    ipyialarmmk.iAlarmMkInterface.DISARMED: AlarmControlPanelState.DISARMED,
    ipyialarmmk.iAlarmMkInterface.TRIGGERED: AlarmControlPanelState.TRIGGERED,
    ipyialarmmk.iAlarmMkInterface.ALARM_ARMING: AlarmControlPanelState.ARMING,
    ipyialarmmk.iAlarmMkInterface.ARMED_PARTIAL: AlarmControlPanelState.ARMED_CUSTOM_BYPASS,
    ipyialarmmk.iAlarmMkInterface.ALARM_DISARMING: AlarmControlPanelState.DISARMING,
    ipyialarmmk.iAlarmMkInterface.UNAVAILABLE: STATE_UNAVAILABLE,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a iAlarm-MK alarm control panel based on a config entry."""
    _LOGGER.info("Set up sensors based on a config entry.")
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Setup with coordinator id: %s", id(coordinator))
    async_add_entities([iAlarmMkPanel(coordinator)], update_before_add=False)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.data[DOMAIN].async_unload_entry(entry.entry_id)


class iAlarmMkPanel(CoordinatorEntity[iAlarmMk2Coordinator], AlarmControlPanelEntity):
    """Representation of an iAlarm-MK device."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:security"

    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS
    )

    def __init__(self, coordinator: iAlarmMk2Coordinator) -> None:
        """Initialize the alarm panel."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.hub.username
        self.code_arm_required = False

    @property
    def alarm_state(self) -> str | None:
        """Return the state of the device."""
        return IALARMMK_TO_HASS.get(self.coordinator.data.alarm_data.state)

    @property
    def extra_state_attributes(self):
        """Ritorna gli attributi personalizzati dinamici."""
        return {"lastRealUpdateStatus": self.coordinator.hub.lastRealUpdateStatus}

    def alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        self._execute_alarm_command(self.coordinator.hub.ialarmmk.disarm)

    def alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        self._execute_alarm_command(self.coordinator.hub.ialarmmk.arm_stay)

    def alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        self._execute_alarm_command(self.coordinator.hub.ialarmmk.arm_away)

    def alarm_arm_custom_bypass(self, code: str | None = None) -> None:
        """Send arm away command."""
        self._execute_alarm_command(self.coordinator.hub.ialarmmk.arm_partial)

    def _execute_alarm_command(self, command: Callable[[str | None], None]) -> None:
        """Expose sanitized command errors to Home Assistant."""
        try:
            command(self._retrive_user_id())
        except AlarmCommandError as err:
            raise HomeAssistantError(str(err)) from None

    @property
    def device_info(self):
        """Device Alarm Info."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.hub.username)},
            "name": self.coordinator.hub.name,
            "manufacturer": "antifurto 365",
            "model": "Centrale Allarme",
            "connections": {(dr.CONNECTION_NETWORK_MAC, self.coordinator.hub.mac)},
        }

    def _retrive_user_id(self) -> str:
        user_id: str = None
        try:
            if self._context.user_id:
                user_id = self._context.user_id
            elif self._context.origin_event.context.user_id:
                user_id = self._context.origin_event.context.user_id
        except AttributeError as e:
            self.logger.error("Error retrieving user_id: %s", e)
        return user_id
