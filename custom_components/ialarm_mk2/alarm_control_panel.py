"""Interfaces with iAlarmMk control panels."""
from __future__ import annotations

import logging

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import libpyialarmmk as ipyialarmmk
from .const import DOMAIN
from .coordinator import iAlarmMk2Coordinator

_LOGGER = logging.getLogger(__name__)

IALARMMK_TO_HASS = {
    ipyialarmmk.iAlarmMkInterface.ARMED_AWAY: AlarmControlPanelState.ARMED_AWAY,
    ipyialarmmk.iAlarmMkInterface.ARMED_STAY: AlarmControlPanelState.ARMED_HOME,
    ipyialarmmk.iAlarmMkInterface.DISARMED: AlarmControlPanelState.DISARMED,
    ipyialarmmk.iAlarmMkInterface.TRIGGERED: AlarmControlPanelState.TRIGGERED,
    ipyialarmmk.iAlarmMkInterface.ALARM_ARMING: AlarmControlPanelState.ARMING,
    ipyialarmmk.iAlarmMkInterface.ARMED_PARTIAL: AlarmControlPanelState.ARMED_CUSTOM_BYPASS,
    ipyialarmmk.iAlarmMkInterface.UNAVAILABLE: STATE_UNAVAILABLE
}

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a iAlarm-MK alarm control panel based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([iAlarmMkPanel(coordinator)])

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.data[DOMAIN].async_unload_entry(entry.entry_id)

class iAlarmMkPanel(
    CoordinatorEntity[iAlarmMk2Coordinator], AlarmControlPanelEntity
):
    """Representation of an iAlarm-MK device."""

    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS
    )
    _attr_name = "iAlarm-MK"
    _attr_icon = "mdi:security"

    def __init__(self, coordinator: iAlarmMk2Coordinator) -> None:
        """Initialize the alarm panel."""
        super().__init__(coordinator)
        self._attr_name = coordinator.hub.name
        self._attr_unique_id = coordinator.hub.mac
        self.code_arm_required = False
        self._attr_device_info = coordinator.hub.device_info

    @property
    def alarm_state(self) -> str | None:
        """Return the state of the device."""
        return IALARMMK_TO_HASS.get(self.coordinator.data.alarm_data.state)

    @property
    def changed_by(self) -> str | None:
        """Return the changed_by of the device."""
        return self.coordinator.hub.changed_by

    @property
    def extra_state_attributes(self):
        """Ritorna gli attributi personalizzati dinamici."""
        return {
            "lastRealUpdateStatus": self.coordinator.hub.lastRealUpdateStatus
        }

    def alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        self.coordinator.hub.ialarmmk.disarm(self._retrive_user_id())

    def alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        self.coordinator.hub.ialarmmk.arm_stay(self._retrive_user_id())

    def alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        self.coordinator.hub.ialarmmk.arm_away(self._retrive_user_id())

    def alarm_arm_custom_bypass(self, code: str | None = None) -> None:
        """Send arm away command."""
        self.coordinator.hub.ialarmmk.arm_partial(self._retrive_user_id())

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


