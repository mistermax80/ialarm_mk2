"""Interfaces with iAlarmMk control panels."""
from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import iAlarmMk2Coordinator, libpyialarmmk as ipyialarmmk
from .const import DOMAIN

IALARMMK_TO_HASS = {
    ipyialarmmk.iAlarmMkInterface.ARMED_AWAY: STATE_ALARM_ARMED_AWAY,
    ipyialarmmk.iAlarmMkInterface.ARMED_STAY: STATE_ALARM_ARMED_HOME,
    ipyialarmmk.iAlarmMkInterface.DISARMED: STATE_ALARM_DISARMED,
    ipyialarmmk.iAlarmMkInterface.TRIGGERED: STATE_ALARM_TRIGGERED,
    ipyialarmmk.iAlarmMkInterface.ALARM_ARMING: STATE_ALARM_ARMING,
    ipyialarmmk.iAlarmMkInterface.UNAVAILABLE: STATE_UNAVAILABLE,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a iAlarm-MK alarm control panel based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([iAlarmMkPanel(coordinator)])


class iAlarmMkPanel(
    CoordinatorEntity[iAlarmMk2Coordinator], AlarmControlPanelEntity
):
    """Representation of an iAlarm-MK device."""

    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
    )
    _attr_name = "iAlarm-MK"
    _attr_icon = "mdi:security"

    def __init__(self, coordinator: iAlarmMk2Coordinator) -> None:
        """Initialize the alarm panel."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.hub.mac
        self.code_arm_required = False
        self._attr_device_info = DeviceInfo(
            manufacturer="iAlarm-MK",
            name=self.name,
            connections={(dr.CONNECTION_NETWORK_MAC, coordinator.hub.mac)},
        )

    @property
    def state(self) -> str | None:
        """Return the state of the device."""
        return IALARMMK_TO_HASS.get(self.coordinator.hub.state)

    def alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        self.coordinator.hub.ialarmmk.disarm()

    def alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        self.coordinator.hub.ialarmmk.arm_stay()

    def alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        self.coordinator.hub.ialarmmk.arm_away()
