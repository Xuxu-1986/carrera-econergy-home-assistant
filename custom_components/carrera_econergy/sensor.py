from homeassistant.helpers.entity import EntityCategory
"""Sensors for Carrera Econergy."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    known_devices = set()

    def add_new_devices():
        rooms = {
            room["uuid"]: room.get("label", "").strip()
            for room in coordinator.data.get("rooms", [])
        }

        entities = []

        for device in coordinator.data.get("devices", []):
            device_id = device.get("_id")

            if not device_id or device_id in known_devices:
                continue

            room_id = device.get("data", {}).get("room")
            room_name = rooms.get(room_id, "Carrera").strip()

            entities.extend([
                CarreraEnergySensor(
                    coordinator,
                    device_id,
                    room_name,
                    "powerConsoToday",
                    "Consommation aujourd'hui",
                ),
                CarreraEnergySensor(
                    coordinator,
                    device_id,
                    room_name,
                    "powerConsoYesterday",
                    "Consommation hier",
                ),
                CarreraErrorSensor(
                    coordinator,
                    device_id,
                    room_name,
                ),
            ])

            known_devices.add(device_id)

        if entities:
            async_add_entities(entities)

    add_new_devices()

    entry.async_on_unload(
        coordinator.async_add_listener(add_new_devices)
    )


class CarreraBaseSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, device_id, room_name):
        super().__init__(coordinator)
        self.device_id = device_id
        self.room_name = room_name

    @property
    def _device(self):
        for device in self.coordinator.data.get("devices", []):
            if device.get("_id") == self.device_id:
                return device
        return {}

    @property
    def device_info(self):
        device = self._device
        data = device.get("data", {})

        model = (
            data.get("model")
            or device.get("model")
            or "Radiateur Econergy"
        )

        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": f"Carrera {self.room_name}",
            "manufacturer": "Carrera",
            "model": str(model),
        }


class CarreraEnergySensor(CarreraBaseSensor):
    """Daily Carrera energy counter.

    Econergy values are currently assumed to be Wh.
    Exposed to Home Assistant as kWh.
    """

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator,
        device_id,
        room_name,
        key,
        label,
    ):
        super().__init__(coordinator, device_id, room_name)

        self.key = key
        self._attr_unique_id = f"carrera_{device_id}_{key}"
        self._attr_name = f"Carrera {room_name} {label}"

    @property
    def native_value(self):
        raw = self._device.get("status", {}).get(self.key)

        if raw is None:
            return None

        try:
            return round(float(raw) / 1000.0, 3)
        except (TypeError, ValueError):
            return None


class CarreraErrorSensor(CarreraBaseSensor):
    """Carrera error code."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, device_id, room_name):
        super().__init__(coordinator, device_id, room_name)

        self._attr_unique_id = f"carrera_{device_id}_error"
        self._attr_name = f"Carrera {room_name} Erreur"

    @property
    def native_value(self):
        return self._device.get("status", {}).get("error")
