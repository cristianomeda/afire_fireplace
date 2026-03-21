from __future__ import annotations

import logging

import requests
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .afire_api import AfireAPI
from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


async def _validate_credentials(hass, username: str, password: str) -> list[dict]:
    api = AfireAPI(username, password)
    try:
        await hass.async_add_executor_job(api.login)
        return await hass.async_add_executor_job(api.get_devices)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (400, 401, 403):
            raise InvalidAuth from exc
        raise CannotConnect from exc
    except requests.RequestException as exc:
        raise CannotConnect from exc
    except Exception as exc:
        message = str(exc).lower()
        if "auth" in message or "credential" in message:
            raise InvalidAuth from exc
        raise CannotConnect from exc


class AfireConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                devices = await _validate_credentials(self.hass, username, password)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception as exc:
                _LOGGER.exception("Unexpected AFIRE validation error: %s", exc)
                errors["base"] = "cannot_connect"
            else:
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    await self.async_set_unique_id(username.strip().lower())
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="AFIRE Fireplace",
                        data={CONF_USERNAME: username, CONF_PASSWORD: password},
                    )

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
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            try:
                devices = await _validate_credentials(self.hass, username, password)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception as exc:
                _LOGGER.exception("Unexpected AFIRE reconfigure error: %s", exc)
                errors["base"] = "cannot_connect"
            else:
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME,
                    default=self.entry.options.get(CONF_USERNAME, self.entry.data.get(CONF_USERNAME)),
                ): cv.string,
                vol.Required(
                    CONF_PASSWORD,
                    default=self.entry.options.get(CONF_PASSWORD, self.entry.data.get(CONF_PASSWORD)),
                ): cv.string,
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)
