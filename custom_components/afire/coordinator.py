from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .afire_api import AfireAPI
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AfireCoordinator(DataUpdateCoordinator[dict]):
    """Shared coordinator for AFIRE fireplaces."""

    def __init__(self, hass: HomeAssistant, api: AfireAPI) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        try:
            devices = await self.hass.async_add_executor_job(self.api.get_devices)
            return {d["did"]: d for d in devices}
        except Exception as err:
            raise UpdateFailed(f"AFIRE update error: {err}") from err

    async def async_set_and_refresh(self, did: str, attrs: dict) -> None:
        """Helper: set attribute and immediately refresh coordinator."""
        await self.hass.async_add_executor_job(self.api.set_attr, did, attrs)
        await self.async_request_refresh()
