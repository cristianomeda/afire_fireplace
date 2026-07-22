from __future__ import annotations

import logging

import requests
from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .afire_api import AfireAPI
from .const import CONF_PASSWORD, CONF_USERNAME, CONF_REGION, DOMAIN
from .coordinator import AfireCoordinator

PLATFORMS = ["switch", "number", "light"]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AFIRE from a config entry."""
    username = entry.options.get(CONF_USERNAME, entry.data[CONF_USERNAME])
    password = entry.options.get(CONF_PASSWORD, entry.data[CONF_PASSWORD])
    region = entry.options.get(CONF_REGION, entry.data[CONF_REGION])

    api = AfireAPI(username, password, region)
    coordinator = AfireCoordinator(hass, api)

    try:
        await hass.async_add_executor_job(api.login)
        await coordinator.async_config_entry_first_refresh()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (400, 401, 403):
            raise ConfigEntryAuthFailed("AFIRE authentication failed") from exc
        raise ConfigEntryNotReady(f"AFIRE service unavailable: {exc}") from exc
    except requests.RequestException as exc:
        raise ConfigEntryNotReady(f"AFIRE service unavailable: {exc}") from exc
    except Exception as exc:
        message = str(exc).lower()
        if "auth" in message or "credential" in message:
            raise ConfigEntryAuthFailed("AFIRE authentication failed") from exc
        raise ConfigEntryNotReady(f"AFIRE setup failed: {exc}") from exc

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when config entry options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload AFIRE config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if data:
            coordinator: AfireCoordinator = data.get("coordinator")
            if coordinator:
                await coordinator.async_shutdown()
    return unload_ok
