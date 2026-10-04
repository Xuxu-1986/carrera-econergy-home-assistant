"""Number platform for Carrera Econergy."""

from homeassistant.components.number import NumberEntity
from homeassistant.const import UnitOfTemperature
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

        new_entities = []

        for device in coordinator.data.get("devices", []):
            device_id = device.get("_id")

            if not device_id or device_id in known_devices:
                continue

            room_id = device.get("data", {}).get("room")
            room_name = rooms.get(room_id, "Carrera")

            new_entities.extend([
                CarreraTemperatureNumber(
                    coordinator, api, device_id, room_name, "eco"
                ),
                CarreraTemperatureNumber(
                    coordinator, api, device_id, room_name, "comfort"
                ),
            ])

            known_devices.add(device_id)

        if new_entities:
            async_add_entities(new_entities)

    add_new_devices()
    entry.async_on_unload(
        coordinator.async_add_listener(add_new_devices)
    )


class CarreraTemperatureNumber(CoordinatorEntity, NumberEntity):
    """Eco or Comfort temperature."""

    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, api, device_id, room_name, kind):
        super().__init__(coordinator)

        self.api = api
        self.device_id = device_id
        self.room_name = room_name
        self.kind = kind

        label = "Eco" if kind == "eco" else "Confort"

        self._attr_unique_id = f"carrera_{device_id}_{kind}"
        self._attr_name = f"Carrera {room_name} {label}"

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

    @property
    def native_value(self):
        return self._device.get("config", {}).get(self.kind)

    @property
    def native_min_value(self):
        if self.kind == "eco":
            return 13.0
        return 17.0

    @property
    def native_max_value(self):
        config = self._device.get("config", {})

        if self.kind == "eco":
            return 19.0

        return float(config.get("setPointLimit", 30))

    async def async_set_native_value(self, value):
        config = self._device.get("config", {}).copy()

        if not config:
            return

        config[self.kind] = value

        await self.hass.async_add_executor_job(
            self.api.set_config,
            self.device_id,
            config,
        )

        await self.coordinator.async_request_refresh()
