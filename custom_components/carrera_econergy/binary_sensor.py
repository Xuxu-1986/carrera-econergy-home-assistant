"""Binary sensors for Carrera Econergy."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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

            entities.append(
                CarreraOpenWindowSensor(
                    coordinator,
                    device_id,
                    room_name,
                )
            )

            known_devices.add(device_id)

        if entities:
            async_add_entities(entities)

    add_new_devices()

    entry.async_on_unload(
        coordinator.async_add_listener(add_new_devices)
    )


class CarreraOpenWindowSensor(CoordinatorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.WINDOW

    def __init__(self, coordinator, device_id, room_name):
        super().__init__(coordinator)

        self.device_id = device_id
        self.room_name = room_name

        self._attr_unique_id = (
            f"carrera_{device_id}_detectedOpenWidows_binary"
        )
        self._attr_name = (
            f"Carrera {room_name} Fenêtre ouverte"
        )

    @property
    def _device(self):
        for device in self.coordinator.data.get("devices", []):
            if device.get("_id") == self.device_id:
                return device
        return {}

    @property
    def is_on(self):
        return bool(
            self._device
            .get("status", {})
            .get("detectedOpenWidows", False)
        )

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
