"""Zone bypass switches for iAlarm-MK2."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
    """Set up zone bypass switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        IAlarmMkZoneBypassSwitch(coordinator, sensor)
        for sensor in coordinator.data.sensors_data
    ]

    async_add_entities(entities)


class IAlarmMkZoneBypassSwitch(
    CoordinatorEntity[iAlarmMk2Coordinator],
    SwitchEntity,
):
    """Control the bypass configuration of an alarm zone."""

    _attr_has_entity_name = True
    _attr_translation_key = "bypass"
    _attr_icon = "mdi:shield-off-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, sensor) -> None:
        """Initialize the bypass switch."""
        super().__init__(coordinator)

        self._zone_index = sensor.index
        self._zone_unique_id = sensor.unique_id

        self._attr_unique_id = f"{sensor.unique_id}_bypass"

    def _get_sensor(self):
        """Get the latest zone data."""
        return next(
            (
                sensor
                for sensor in self.coordinator.data.sensors_data
                if sensor.index == self._zone_index
            ),
            None,
        )

    @property
    def available(self) -> bool:
        """Return whether zone status is available."""
        sensor = self._get_sensor()

        return (
            super().available
            and sensor is not None
            and sensor.last_fetch_time is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return the current bypass state."""
        sensor = self._get_sensor()

        if sensor is None or sensor.last_fetch_time is None:
            return None

        return bool(sensor.state & self.coordinator.hub.ialarmmk.ZONE_BYPASS)

    @property
    def device_info(self):
        """Associate the switch with the existing zone device."""
        return {
            "identifiers": {(DOMAIN, self._zone_unique_id)},
        }

    async def _async_set_bypass(self, enabled: bool) -> None:
        """Set zone bypass and verify the result."""
        coordinator = self.coordinator
        alarm = coordinator.hub.ialarmmk

        if (
            not coordinator.last_update_success
            or coordinator.data.alarm_data.state != alarm.DISARMED
        ):
            raise HomeAssistantError(
                "Alarm must be available and disarmed before modifying zone bypass."
            )

        _LOGGER.info(
            "Setting zone bypass: zone=%s, enabled=%s.",
            self._zone_index,
            enabled,
        )

        try:
            await self.hass.async_add_executor_job(
                alarm.set_zone_bypass,
                self._zone_index,
                enabled,
            )
        except Exception as err:
            _LOGGER.exception(
                "Failed to set zone %s bypass.",
                self._zone_index,
            )
            raise HomeAssistantError("Unable to send zone bypass command.") from err

        try:
            await coordinator.async_request_refresh()
        except Exception as err:
            raise HomeAssistantError(
                "Bypass command sent, but state refresh failed."
            ) from err

        if not coordinator.last_update_success:
            raise HomeAssistantError("Bypass command sent, but state refresh failed.")

        sensor = self._get_sensor()

        if sensor is None or sensor.last_fetch_time is None:
            raise HomeAssistantError("Zone status unavailable after bypass command.")

        actual_state = bool(sensor.state & alarm.ZONE_BYPASS)

        if actual_state != enabled:
            raise HomeAssistantError("Bypass state does not match the requested value.")

        _LOGGER.info(
            "Zone bypass verified: zone=%s, enabled=%s.",
            self._zone_index,
            enabled,
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Enable bypass."""
        await self._async_set_bypass(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable bypass."""
        await self._async_set_bypass(False)
