"""Componente per porte e finestre."""

import logging

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
        self.hass = coordinator.hass
        self._attr_unique_id = unique_id
        self.name = name
        self.entity_id = entity_id
        self.index: int = index
        self._attr_is_on = None
        self._attr_state = None
        #Types: 0: Disabilitata, 1: Ritardata, 2: Perimetrale, 3:Interna, 4: Emergenza, 5: Attiva 24 ore, 6: Incendio, 7: Chiavi
        match zone_type:
            case 1 | 2:
                if(self.name.lower().find("port")>0):
                    self._attr_device_class = BinarySensorDeviceClass.DOOR
                elif(self.name.lower().find("intern")>0):
                    self._attr_device_class = BinarySensorDeviceClass.MOTION
                else:
                    self._attr_device_class = BinarySensorDeviceClass.WINDOW
            case 3:
                self._attr_device_class = BinarySensorDeviceClass.MOTION
            case 4 | 5:
                self._attr_device_class = BinarySensorDeviceClass.PROBLEM
            case 6:
                if(self.name.lower().find("gas")>0):
                    self._attr_device_class = BinarySensorDeviceClass.GAS
                else:
                    self._attr_device_class = BinarySensorDeviceClass.SMOKE
            case 0 | _:
                self._attr_device_class = BinarySensorDeviceClass.OPENING
        self._low_battery:bool = None
        self._loss:bool = None
        self._bypass:bool = None
        self._last_check = None

    def set_attr_is_on(self, state:bool):
        '''set_attr_is_on.'''
        self._attr_is_on = state

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
    def extra_state_attributes(self):
        """Ritorna gli attributi personalizzati dinamici."""
        return {
            "low_battery": self._low_battery,
            "loss": self._loss,
            "bypass": self._bypass,
            "last_check": self._last_check,
        }

    '''
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.info("Handle updated data from the coordinator.")
        #state = self.coordinator.sensors[self.index].get("state")
        _LOGGER.info(f"{self.name} {self.index} {self.coordinator.sensors[self.index]}")
        #self._attr_is_on = self.coordinator.data[self.index].get("state")
        self.async_write_ha_state()

    def update(self) -> None:
        """Fetch new state data for the sensor."""
        _LOGGER.info("Fetch new state data for the sensor.")
        self._attr_is_on = False
        #await self.coordinator.async_request_refresh()
    '''
