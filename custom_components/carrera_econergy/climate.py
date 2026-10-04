"""Climate platform for Carrera Econergy."""

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


MODE_TO_PRESET = {
    1: "Hors gel",
    3: "Manu",
    4: "Prog",
    6: "Pilot",
}

PRESET_TO_MODE = {
    value: key for key, value in MODE_TO_PRESET.items()
}


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

            new_entities.append(
                CarreraClimate(
                    coordinator,
                    api,
                    device_id,
                    room_name,
                )
            )

            known_devices.add(device_id)

        if new_entities:
            async_add_entities(new_entities)

    add_new_devices()

    entry.async_on_unload(
        coordinator.async_add_listener(add_new_devices)
    )


class CarreraClimate(CoordinatorEntity, ClimateEntity):
    """Carrera radiator."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT

    @property
    def extra_state_attributes(self):
        return {
            "econergy_device_id": self.device_id,
        }

    @property
    def supported_features(self):
        mode = self._device.get("config", {}).get("mode")

        features = ClimateEntityFeature.PRESET_MODE

        # Hors gel : consigne fixe, aucun réglage de température
        if mode != 1:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE

        return features

    _attr_preset_modes = [
        "Manu",
        "Prog",
        "Pilot",
        "Hors gel",
    ]

    _attr_target_temperature_step = 0.5

    @property
    def min_temp(self):
        config = self._device.get("config", {})
        status = self._device.get("status", {})

        mode = config.get("mode")
        state = status.get("state")

        # Hors gel : valeur fixe
        if mode == 1:
            return 7.0

        # Programme Eco
        if mode == 4 and state == 2:
            return 13.0

        # Pilot Eco : la consigne effective peut descendre
        # 3,5 °C sous le setPoint minimal de 17 °C
        if mode == 6 and state == 2:
            return 13.5

        # Manu, Prog Confort et Pilot Confort
        return 17.0

    @property
    def max_temp(self):
        config = self._device.get("config", {})
        status = self._device.get("status", {})

        mode = config.get("mode")
        state = status.get("state")

        # Hors gel : valeur fixe
        if mode == 1:
            return 7.0

        # Programme Eco : plage Carrera 13 -> 19 °C
        if mode == 4 and state == 2:
            return 19.0

        limit = config.get("setPointLimit")
        return float(limit) if limit is not None else 30.0

    def __init__(self, coordinator, api, device_id, room_name):
        super().__init__(coordinator)

        self.api = api
        self.device_id = device_id
        self.room_name = room_name

        self._attr_unique_id = f"carrera_{device_id}"
        self._attr_name = f"Carrera {room_name}"

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
    def current_temperature(self):
        return self._device.get("status", {}).get("temperature")

    @property
    def target_temperature(self):
        config = self._device.get("config", {})
        status = self._device.get("status", {})

        mode = config.get("mode")
        state = status.get("state")

        setpoint = config.get("setPoint")
        eco = config.get("eco")
        comfort = config.get("comfort")

        # Hors gel
        if mode == 1:
            return 7.0

        # Manuel
        if mode == 3:
            return setpoint

        # Programme
        if mode == 4:
            if state == 2:
                return eco
            if state == 3:
                return comfort

        # Fil pilote
        if mode == 6:
            if state == 2 and setpoint is not None:
                return setpoint - 3.5
            if state == 3:
                return setpoint

        # Valeur de secours
        return setpoint

    @property
    def preset_mode(self):
        mode = self._device.get("config", {}).get("mode")
        return MODE_TO_PRESET.get(mode)

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get("temperature")

        if temperature is None:
            return

        config = self._device.get("config", {}).copy()
        status = self._device.get("status", {})

        if not config:
            return

        mode = config.get("mode")
        state = status.get("state")

        # Hors gel : consigne fixe à 7 °C
        if mode == 1:
            return

        # Programme : modifier la consigne actuellement active
        if mode == 4:
            if state == 2:
                # Eco : plage 13 -> 19 °C
                temperature = max(13.0, min(19.0, temperature))
                config["eco"] = temperature
            elif state == 3:
                # Confort : plage 17 °C -> limite maxi
                limit = float(config.get("setPointLimit", 30))
                temperature = max(17.0, min(limit, temperature))
                config["comfort"] = temperature
            else:
                return

        else:
            # Manu / Pilot : setPoint 17 °C -> limite maxi
            limit = float(config.get("setPointLimit", 30))
            temperature = max(17.0, min(limit, temperature))
            config["setPoint"] = temperature

        await self.hass.async_add_executor_job(
            self.api.set_config,
            self.device_id,
            config,
        )

        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode):
        mode = PRESET_TO_MODE.get(preset_mode)

        if mode is None:
            return

        config = self._device.get("config", {}).copy()

        if not config:
            return

        config["mode"] = mode

        await self.hass.async_add_executor_job(
            self.api.set_config,
            self.device_id,
            config,
        )

        await self.coordinator.async_request_refresh()
