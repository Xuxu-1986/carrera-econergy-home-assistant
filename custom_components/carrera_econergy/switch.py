"""Switch platform for Carrera Econergy."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
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
            room_name = rooms.get(room_id, "Carrera")

            for day in range(1, 8):
                for slot in range(3):
                    entities.append(
                        CarreraProgramSwitch(
                            coordinator, api, device_id,
                            room_name, day, slot
                        )
                    )

            known_devices.add(device_id)

        if entities:
            async_add_entities(entities)

    add_new_devices()

    entry.async_on_unload(
        coordinator.async_add_listener(add_new_devices)
    )


class CarreraProgramSwitch(CoordinatorEntity, SwitchEntity):
    """Enable or disable a Carrera program slot."""

    def __init__(
        self, coordinator, api, device_id, room_name, day, slot
    ):
        super().__init__(coordinator)

        self.api = api
        self.device_id = device_id
        self.room_name = room_name
        self.day = day
        self.slot = slot

        days = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

        self._attr_unique_id = (
            f"carrera_{device_id}_day{day}_slot{slot + 1}_active"
        )
        self._attr_name = (
            f"Carrera {room_name} {days[day - 1]} "
            f"plage {slot + 1}"
        )

    @property
    def device_info(self):
        device = self._device
        data = device.get("data", {})

        room_name = getattr(self, "room_name", None)

        if not room_name:
            name = getattr(self, "_attr_name", "Carrera")
            room_name = name.replace("Carrera ", "").split(" ")[0]

        model = (
            data.get("model")
            or device.get("model")
            or "Radiateur Econergy"
        )

        return {
            "identifiers": {
                (DOMAIN, self.device_id)
            },
            "name": f"Carrera {room_name}",
            "manufacturer": "Carrera",
            "model": str(model),
        }

    @property
    def _device(self):
        for device in self.coordinator.data.get("devices", []):
            if device.get("_id") == self.device_id:
                return device
        return {}

    def _program(self):
        programs = self._device.get("config", {}).get("programs", [])
        day_programs = [p for p in programs if p.get("day") == self.day]

        if self.slot >= len(day_programs):
            return None

        return day_programs[self.slot]

    @property
    def is_on(self):
        program = self._program()
        return bool(program and program.get("isActive"))

    async def _set_active(self, active):
        device = self._device
        config = device.get("config", {}).copy()
        programs = [p.copy() for p in config.get("programs", [])]

        day_indexes = [
            i for i, p in enumerate(programs)
            if p.get("day") == self.day
        ]

        if self.slot >= len(day_indexes):
            return

        index = day_indexes[self.slot]

        if active:
            # N'activer que si des horaires valides existent déjà.
            start = programs[index].get("startTime", 1440)
            end = programs[index].get("endTime", 1440)

            if start >= 1440 or end >= 1440 or start >= end:
                return

            programs[index]["isActive"] = True

        else:
            # Format natif Econergy pour une plage inutilisée.
            programs[index]["isActive"] = False
            programs[index]["startTime"] = 1440
            programs[index]["endTime"] = 1440

        await self.hass.async_add_executor_job(
            self.api.set_programs,
            self.device_id,
            programs,
        )

        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._set_active(True)

    async def async_turn_off(self, **kwargs):
        await self._set_active(False)
