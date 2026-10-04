"""Data coordinator for Carrera Econergy."""

from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)


class CarreraEconergyCoordinator(DataUpdateCoordinator):
    """Fetch the complete Econergy home periodically."""

    def __init__(self, hass, api):
        self.api = api
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Carrera Econergy",
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.api.get_home)
        except Exception as err:
            raise UpdateFailed(f"Unable to update Econergy data: {err}") from err
