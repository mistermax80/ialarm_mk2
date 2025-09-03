"""Componente per porte e finestre."""

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    if hasattr(coordinator, "sensors"):
        async_add_entities(coordinator.sensors, update_before_add=False)
    _LOGGER.debug(
        "Set up %d sensors: %s",
        len(coordinator.sensors),
        [s.name for s in coordinator.sensors],
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.data[DOMAIN].async_unload_entry(entry.entry_id)


class IAlarmmkSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a iAlarm Status Sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        name: str,
        index: int,
        unique_id: str,
        zone_type: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_index: int = index
        self._attr_zone_type: str = zone_type
        self._attr_low_battery: bool = None
        self._attr_loss: bool = None
        self._attr_bypass: bool = None
        self._attr_last_check = None

    @property
    def is_on(self) -> bool | None:
        """Return whether the sensor is on."""
        _LOGGER.debug("Getting is_on for sensor index: %s", self._attr_index)
        self._sensor_map = {s.index: s for s in self.coordinator.data.sensors_data}
        sensor = self._sensor_map.get(self._attr_index)
        return sensor.is_on if sensor else None

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of this entity."""
        # Types: 0: Disabilitata, 1: Ritardata, 2: Perimetrale, 3:Interna, 4: Emergenza, 5: Attiva 24 ore, 6: Incendio, 7: Chiavi
        match self._attr_zone_type:
            case 1 | 2:
                if "port" in self._attr_name.lower():
                    return BinarySensorDeviceClass.DOOR
                if "intern" in self._attr_name.lower():
                    return BinarySensorDeviceClass.MOTION
                return BinarySensorDeviceClass.WINDOW
            case 3:
                return BinarySensorDeviceClass.MOTION
            case 4 | 5:
                return BinarySensorDeviceClass.PROBLEM
            case 6:
                if "gas" in self._attr_name.lower():
                    return BinarySensorDeviceClass.GAS
                return BinarySensorDeviceClass.SMOKE
            case 0 | _:
                return BinarySensorDeviceClass.OPENING
        return None

    @property
    def index(self) -> int:
        """Return sensor index."""
        return self._attr_index

    def set_extra_state_attributes(
        self, low_battery: bool, loss: bool, bypass: bool, last_check
    ):
        """set_extra_state_attributes."""
        self._attr_low_battery = low_battery
        self._attr_loss = loss
        self._attr_bypass = bypass
        self._attr_last_check = last_check

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Ritorna gli attributi personalizzati dinamici."""
        return {
            "low_battery": self._attr_low_battery,
            "loss": self._attr_loss,
            "bypass": self._attr_bypass,
            "last_check": self._attr_last_check,
        }

    @property
    def device_info(self):
        """Device Sensor Info."""
        return {
            "identifiers": {(DOMAIN, self._attr_name)},
            "name": self._attr_name,
            "manufacturer": "antifurto 365",
            "model": "Sensor",
            "via_device": (DOMAIN, self.coordinator.hub.username),
        }
