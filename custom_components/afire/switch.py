from __future__ import annotations

import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AfireCoordinator

_LOGGER = logging.getLogger(__name__)

SUPPORTED_SWITCHES = {
    "POWERSW": ("Power", "mdi:fireplace"),
    "COLOR_SW": ("RGB LEDs", "mdi:palette"),
    "LED_SW": ("Amber LEDs", "mdi:wall-sconce-round-variant")
}

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: AfireCoordinator = data["coordinator"]
    api = data["api"]

    entities: list[AfireSwitch] = []
    for did, dev in coordinator.data.items():
        attrs = dev.get("attrs", {})
        for key, (label, icon) in SUPPORTED_SWITCHES.items():
            if key in attrs:
                entities.append(AfireSwitch(coordinator, api, did, dev, label, key, icon))
    async_add_entities(entities)


class AfireSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator: AfireCoordinator, api, did: str, dev: dict, label: str, key: str, icon: str):
        super().__init__(coordinator)
        self.api = api
        self.did = did
        self.dev = dev
        self._key = key

        base_name = dev.get("alias") or dev.get("name", "Fireplace")
        if base_name.upper() == "AFIRE":
            base_name = "Fireplace"
        self._attr_name = f"{base_name} {label}"
        self._attr_unique_id = f"{did.lower()}_{key.lower()}"
        self._attr_icon = icon

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.did)},
            "name": self.dev.get("alias") or self.dev.get("name", "Fireplace"),
            "manufacturer": "AFIRE",
            "model": self.dev.get("model", "UNKNOWN"),
        }

    @property
    def is_on(self) -> bool:
        status = self.coordinator.data.get(self.did, {}).get("attrs", {})
        return bool(status.get(self._key, 0))

    @property
    def is_fireplace_on(self) -> bool:
        status = self.coordinator.data.get(self.did, {}).get("attrs", {})
        return bool(status.get("POWERSW", 0))

    async def async_turn_on(self, **kwargs):
        if self._key != "POWERSW" and not self.is_fireplace_on:
            _LOGGER.warning("Fireplace %s is OFF — cannot turn on %s", self.did, self._key)
            return
        await self.hass.async_add_executor_job(self.api.set_attr, self.did, {self._key: 1})
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self.api.set_attr, self.did, {self._key: 0})
        await self.coordinator.async_request_refresh()
