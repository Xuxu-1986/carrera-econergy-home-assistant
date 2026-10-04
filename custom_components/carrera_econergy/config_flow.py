"""Config flow for Carrera Econergy."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .api import EconergyApi, EconergyAuthError, EconergyConnectionError
from .const import DOMAIN


class CarreraEconergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Carrera Econergy configuration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            api = EconergyApi(
                user_input[CONF_EMAIL],
                user_input[CONF_PASSWORD],
            )
            try:
                result = await self.hass.async_add_executor_job(api.authenticate)
            except EconergyAuthError:
                errors["base"] = "invalid_auth"
            except EconergyConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(result["homeId"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=result.get("homeName", "Carrera Econergy"),
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        "home_id": result["homeId"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )
