from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .afire_api import AfireAPI
from .const import DOMAIN, POLL_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class AfireCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Shared coordinator for AFIRE fireplaces."""

    def __init__(self, hass: HomeAssistant, api: AfireAPI) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=POLL_INTERVAL_SECONDS),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            if not self.api.devices:
                # Discovery is cached after the first refresh; later updates only
                # re-read device state for the known merged device list.
                devices = await self.hass.async_add_executor_job(self.api.get_devices)
            else:
                devices = self.api.devices

            async def fetch_status(did: str) -> dict[str, Any]:
                return await self.hass.async_add_executor_job(self.api.get_status, did)

            dids = [device["did"] for device in devices]
            statuses = await asyncio.gather(*(fetch_status(did) for did in dids))

            results: dict[str, dict[str, Any]] = {}
            for device, attrs in zip(devices, statuses):
                device["attrs"] = attrs
                results[device["did"]] = device

            self.api.devices = list(results.values())
            return results
        except Exception as err:
            raise UpdateFailed(f"AFIRE update error: {err}") from err

    async def async_set_device_attrs(self, did: str, attrs: dict[str, Any]) -> None:
        """Apply device attrs and schedule a validation refresh if required."""
        result = await self.hass.async_add_executor_job(self.api.set_attr, did, attrs)

        if did in self.data:
            # AWPR2 commands can take a moment to settle in the cloud service, so
            # entities get an optimistic state immediately and a delayed refresh
            # later validates what the fireplace actually reported back.
            self.data[did]["attrs"].update(result.get("attrs", {}))
            self.async_set_updated_data(dict(self.data))

        refresh_delay = float(result.get("refresh_delay", 0) or 0)
        if refresh_delay > 0:
            async_call_later(
                self.hass,
                refresh_delay,
                lambda _: self.hass.async_create_task(self.async_request_refresh()),
            )
        else:
            await self.async_request_refresh()
