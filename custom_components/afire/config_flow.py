from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from .afire_api import AfireAPI

_LOGGER = logging.getLogger(__name__)


class AfireConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            api = AfireAPI(username, password)

            try:
                await self.hass.async_add_executor_job(api.login)
                devices = await self.hass.async_add_executor_job(api.get_devices)
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    return self.async_create_entry(
                        title="AFIRE Fireplace",
                        data={CONF_USERNAME: username, CONF_PASSWORD: password},
                    )
            except Exception as exc:
                _LOGGER.error("AFIRE auth failed: %s", exc)
                errors["base"] = "auth"

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AfireOptionsFlow(config_entry)


class AfireOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_reconfigure()

    async def async_step_reconfigure(self, user_input=None):
        errors = {}
        if user_input:
            # Save updated creds into options; integration can read from entry.options
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=self.entry.data.get(CONF_USERNAME)): cv.string,
                vol.Required(CONF_PASSWORD, default=self.entry.data.get(CONF_PASSWORD)): cv.string,
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)
