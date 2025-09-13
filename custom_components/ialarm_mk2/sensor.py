"""Platform for sensor integration."""

from __future__ import annotations

from datetime import date
import logging

from homeassistant.components.sensor import Any, SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors based on a config entry."""
    _LOGGER.info("Set up sensors based on a config entry.")
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Setup with coordinator id: %s", id(coordinator))
    if hasattr(coordinator, "data") and hasattr(coordinator.data, "sensors_data"):
        _LOGGER.debug(
            "Set up %d sensors: %s",
            len(coordinator.data.sensors_data),
            [s.zone_name for s in coordinator.data.sensors_data],
        )
        list_sensors: list[IAlarmmkSensorBattery] = []
        for sc in coordinator.data.sensors_data:
            iAlarmSensor = IAlarmmkSensorBattery(
                coordinator,
                sc.zone_name,
                sc.index,
                sc.unique_id,
            )
            list_sensors.append(iAlarmSensor)
        async_add_entities(list_sensors, update_before_add=False)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.data[DOMAIN].async_unload_entry(entry.entry_id)


class IAlarmmkSensorBattery(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    _attr_has_entity_name = True
    _attr_name = "Battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = "%"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        zone_name: str,
        index: int,
        unique_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_index: int = index
        self._attr_zone_name: str = zone_name

    @property
    def index(self) -> int:
        """Return sensor index."""
        return self._attr_index

    @property
    def zone_name(self) -> int:
        """Return sensor index."""
        return self._attr_zone_name

    @property
    def native_value(self) -> int:
        """Return battery charge percentage based on last change date."""
        # Mappa index → sensore
        self._sensor_map = {s.index: s for s in self.coordinator.data.sensors_data}
        sensor = self._sensor_map.get(self._attr_index)

        if (sensor.state & self.coordinator.hub.ialarmmk.ZONE_LOW_BATTERY):
            return 5

        if not sensor or not sensor.last_battery_change_date:
            return None  # default se mancante

        # Durata media della batteria: 2 anni
        BATTERY_LIFETIME_DAYS = 365 * 2

        # Converte stringa ISO in oggetto date, se necessario
        if isinstance(sensor.last_battery_change_date, str):
            try:
                last_change = date.fromisoformat(sensor.last_battery_change_date)
            except ValueError:
                _LOGGER.warning("Invalid date '%s' for sensor %s, ignoring", sensor.last_battery_change_date, sensor.zone_name)
                return None
        else:
            last_change = sensor.last_battery_change_date

        # Giorni trascorsi dall'ultimo cambio
        days_elapsed = (date.today() - last_change).days

        # Percentuale residua
        return max(0, min(100, int((1 - days_elapsed / BATTERY_LIFETIME_DAYS) * 100)))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Ritorna gli attributi personalizzati dinamici."""
        self._sensor_map = {s.index: s for s in self.coordinator.data.sensors_data}
        sensor = self._sensor_map.get(self._attr_index)
        return {
            "zone_number": self._attr_index,
            "serial_number": self._attr_unique_id,
            "last_battery_change_date": sensor.last_battery_change_date,
        }

    @property
    def device_info(self):
        """Device Sensor Info."""
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
        }
