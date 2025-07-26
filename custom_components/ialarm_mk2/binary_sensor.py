"""Componente per porte e finestre."""

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
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
    if hasattr(coordinator, "sensors"):
        async_add_entities(coordinator.sensors,True)
    _LOGGER.debug(coordinator.sensors)

class IAlarmmkSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a iAlarm Status Sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device: DeviceInfo,
        name: str,
        index: int,
        entity_id: str,
        unique_id: str,
        zone_type: int
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_info = device
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_entity_id = entity_id
        self._attr_index: int = index
        #Types: 0: Disabilitata, 1: Ritardata, 2: Perimetrale, 3:Interna, 4: Emergenza, 5: Attiva 24 ore, 6: Incendio, 7: Chiavi
        match zone_type:
            case 1 | 2:
                if "port" in name.lower():
                    self._attr_device_class = BinarySensorDeviceClass.DOOR
                elif("intern" in name.lower()):
                    self._attr_device_class = BinarySensorDeviceClass.MOTION
                else:
                    self._attr_device_class = BinarySensorDeviceClass.WINDOW
            case 3:
                self._attr_device_class = BinarySensorDeviceClass.MOTION
            case 4 | 5:
                self._attr_device_class = BinarySensorDeviceClass.PROBLEM
            case 6:
                if("gas" in name.lower()):
                    self._attr_device_class = BinarySensorDeviceClass.GAS
                else:
                    self._attr_device_class = BinarySensorDeviceClass.SMOKE
            case 0 | _:
                self._attr_device_class = BinarySensorDeviceClass.OPENING
        self._attr_is_on = None
        self._attr_low_battery:bool = None
        self._attr_loss:bool = None
        self._attr_bypass:bool = None
        self._attr_last_check = None

    def set_attr_is_on(self, state:bool):
        '''set_attr_is_on.'''
        self._attr_is_on = state

    @property
    def is_on(self) -> bool | None:
        '''is_on.'''
        return self._attr_is_on

    @property
    def index(self) -> bool | None:
        '''is_on.'''
        return self._attr_index

    def set_state(self, state):
        '''set_state.'''
        self._attr_state = state

    def set_extra_state_attributes(self,low_battery:bool,loss:bool,bypass:bool,last_check):
        '''set_extra_state_attributes.'''
        self._low_battery = low_battery
        self._loss = loss
        self._bypass = bypass
        self._last_check = last_check

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Ritorna gli attributi personalizzati dinamici."""
        return {
            "low_battery": self._low_battery,
            "loss": self._loss,
            "bypass": self._bypass,
            "last_check": self._last_check,
        }
