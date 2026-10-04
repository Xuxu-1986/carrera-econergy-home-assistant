"""Carrera Econergy integration."""

from homeassistant.exceptions import HomeAssistantError

from .api import EconergyApi
from .const import DOMAIN, PLATFORMS
from .coordinator import CarreraEconergyCoordinator


def _entry_for_device(hass, device_id):
    for entry_data in hass.data.get(DOMAIN, {}).values():
        devices = entry_data["coordinator"].data.get("devices", [])
        if any(device.get("_id") == device_id for device in devices):
            return entry_data
    return None


async def _async_set_programs_service(hass, call):
    """Save a complete weekly program to Econergy."""
    device_id = call.data.get("device_id")
    programs = call.data.get("programs")

    if not device_id or not isinstance(programs, list):
        raise HomeAssistantError("device_id and programs are required")
    if len(programs) != 21:
        raise HomeAssistantError("Exactly 21 program slots are required")

    entry_data = _entry_for_device(hass, device_id)
    if entry_data is None:
        raise HomeAssistantError("Carrera Econergy device not found")

    await hass.async_add_executor_job(
        entry_data["api"].set_programs, device_id, programs
    )
    await entry_data["coordinator"].async_request_refresh()


async def async_setup_entry(hass, entry):
    api = EconergyApi(entry.data["email"], entry.data["password"])
    await hass.async_add_executor_job(api.authenticate)

    coordinator = CarreraEconergyCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"api": api, "coordinator": coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, "set_programs"):
        async def handle_set_programs(call):
            await _async_set_programs_service(hass, call)

        hass.services.async_register(DOMAIN, "set_programs", handle_set_programs)

    return True


async def async_unload_entry(hass, entry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN] and hass.services.has_service(DOMAIN, "set_programs"):
            hass.services.async_remove(DOMAIN, "set_programs")
    return unloaded
