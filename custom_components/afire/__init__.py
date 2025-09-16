from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from .afire_api import AfireAPI
from .coordinator import AfireCoordinator

PLATFORMS = ["switch", "number", "light"]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AFIRE from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    # Use options override if present (reconfigure flow)
    username = entry.options.get(CONF_USERNAME, username)
    password = entry.options.get(CONF_PASSWORD, password)

    api = AfireAPI(username, password)
    coordinator = AfireCoordinator(hass, api)

    # Initial login + first refresh (discovery)
    try:
        await hass.async_add_executor_job(api.login)
        await coordinator.async_config_entry_first_refresh()
    except Exception as exc:
        _LOGGER.error("AFIRE setup failed: %s", exc)
        return False

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload AFIRE config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
