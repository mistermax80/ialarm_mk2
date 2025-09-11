"""Componente per porte e finestre."""

import logging
import time
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

from . import libpyialarmmk as ipyialarmmk
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
        [s.zone_name for s in coordinator.sensors],
    )

    if hasattr(coordinator, "connectivity_sensor"):
        async_add_entities(coordinator.connectivity_sensor, update_before_add=True)
    _LOGGER.debug(
        "Set up %d connectivity_sensor: %s",
        len(coordinator.connectivity_sensor),
        list(coordinator.connectivity_sensor),
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.data[DOMAIN].async_unload_entry(entry.entry_id)


class IAlarmmkSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a iAlarm Status Sensor."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        zone_name: str,
        index: int,
        unique_id: str,
        zone_type: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_index: int = index
        self._attr_zone_name: str = zone_name
        self._attr_zone_type: str = zone_type
        self._attr_low_battery: bool = None
        self._attr_loss: bool = None
        self._attr_bypass: bool = None
        self._attr_last_check = None

    @property
    def is_on(self) -> bool | None:
        """Return whether the sensor is on."""
        log_message= f"Getting is_on for sensor: {self._attr_zone_name}({self._attr_index}) --> "
        self._sensor_map = {s.index: s for s in self.coordinator.data.sensors_data}
        sensor = self._sensor_map.get(self._attr_index)
        _value_is_on = None

        log_message += f"{sensor.state}: "

        # Verifica se la zona è persa
        if sensor.state & ipyialarmmk.iAlarmMkInterface.ZONE_LOSS:
            _value_is_on = None
            log_message += f"(Persa) {bin(sensor.state)}"
        # Verifica se la zona non è utilizzata
        elif sensor.state == ipyialarmmk.iAlarmMkInterface.ZONE_NOT_USED:
            _value_is_on = None
            log_message += f"(Non Usato) {bin(sensor.state)}"
        # Verifica se la zona è in uso
        elif sensor.state & ipyialarmmk.iAlarmMkInterface.ZONE_IN_USE:
            # Verifica se la zona è in uso e in fault (aperto)
            if sensor.state & ipyialarmmk.iAlarmMkInterface.ZONE_FAULT:
                _value_is_on = True
                log_message += f"(Aperto) {bin(sensor.state)}"
            # Verifica se la zona è in uso e non in fault (chiuso)
            else:
                _value_is_on = False
                log_message += f"(Chiuso) {bin(sensor.state)}"
        else:
            _value_is_on = None
            _LOGGER.warning(
                "%s: sensor.state (Sconosciuto) %s \n", sensor.zone_name, bin(sensor.state)
            )

        _LOGGER.debug(log_message)
        return _value_is_on

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of this entity."""
        # Types: 0: Disabilitata, 1: Ritardata, 2: Perimetrale, 3:Interna, 4: Emergenza, 5: Attiva 24 ore, 6: Incendio, 7: Chiavi
        match self._attr_zone_type:
            case 1 | 2:
                if "port" in self._attr_zone_name.lower():
                    return BinarySensorDeviceClass.DOOR
                if "intern" in self._attr_zone_name.lower():
                    return BinarySensorDeviceClass.MOTION
                return BinarySensorDeviceClass.WINDOW
            case 3:
                return BinarySensorDeviceClass.MOTION
            case 4 | 5:
                return BinarySensorDeviceClass.PROBLEM
            case 6:
                if "gas" in self._attr_zone_name.lower():
                    return BinarySensorDeviceClass.GAS
                return BinarySensorDeviceClass.SMOKE
            case 0 | _:
                return BinarySensorDeviceClass.OPENING
        return None

    @property
    def index(self) -> int:
        """Return sensor index."""
        return self._attr_index

    @property
    def zone_name(self) -> int:
        """Return sensor index."""
        return self._attr_zone_name

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
            "zone_number": self._attr_index,
            "serial_number": self._attr_unique_id,
            "low_battery": self._attr_low_battery,
            "loss": self._attr_loss,
            "bypass": self._attr_bypass,
            "last_check": self._attr_last_check,
        }

    @property
    def device_info(self):
        """Device Sensor Info."""
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": self._attr_zone_name,
            "serial_number": self._attr_unique_id,
            "manufacturer": "antifurto 365",
            "model": "Sensore",
            "via_device": (DOMAIN, self.coordinator.hub.username),
        }


class IAlarmmkConnectivity(CoordinatorEntity, BinarySensorEntity):
    """Representation of a iAlarm Status Sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.hub.username
        self._attr_name = "Connectivity"
        self._attr_last_keeplive_ts = None

    @property
    def is_on(self) -> bool | None:
        """Return whether the sensor is on."""
        last_ts = self.coordinator.data.alarm_data.last_keeplive_ts
        _LOGGER.debug("Retrieve last keeplive timestamp: %s", last_ts)
        self._attr_last_keeplive_ts = last_ts
        if last_ts is None:
            # nessun keepalive ricevuto → consideriamo spento
            return False
        # differenza in secondi tra ora corrente e ultimo keepalive
        diff = time.time() - last_ts
        # se l'ultimo keepalive è entro 5 minuti → True, altrimenti False
        return diff <= 5 * 60

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of this entity."""
        return BinarySensorDeviceClass.CONNECTIVITY

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Aggiunge info aggiuntive sullo stato."""
        last_ts = self.coordinator.data.alarm_data.last_keeplive_ts
        if last_ts is not None:
            return {"Last keeplive timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_ts))}
        return {"Last keeplive timestamp": None}

    @property
    def device_info(self):
        """Device Sensor Info."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.hub.username)},
        }
