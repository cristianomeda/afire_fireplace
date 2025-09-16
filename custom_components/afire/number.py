from __future__ import annotations

import logging
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AfireCoordinator

_LOGGER = logging.getLogger(__name__)

SUPPORTED_NUMBERS = {
    "FLAME": ("Flame Height", 0, 5, 1, "mdi:fire"),
    "SPEED": ("Flame Speed", 0, 5, 1, "mdi:fan"),
}


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: AfireCoordinator = data["coordinator"]
    api = data["api"]

    entities: list[AfireNumber] = []
    for did, dev in coordinator.data.items():
        attrs = dev.get("attrs", {})
        for key, (label, min_v, max_v, step, icon) in SUPPORTED_NUMBERS.items():
            if key in attrs:
                entities.append(
                    AfireNumber(coordinator, api, did, dev, label, key, min_v, max_v, step, icon)
                )
    async_add_entities(entities)


class AfireNumber(CoordinatorEntity, NumberEntity):
    def __init__(
        self,
        coordinator: AfireCoordinator,
        api,
        did: str,
        dev: dict,
        label: str,
        key: str,
        min_value: int,
        max_value: int,
        step: int,
        icon: str,
    ):
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
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
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
    def native_value(self):
        status = self.coordinator.data.get(self.did, {}).get("attrs", {})
        val = status.get(self._key)
        return int(val) if val is not None else None

    @property
    def is_fireplace_on(self) -> bool:
        status = self.coordinator.data.get(self.did, {}).get("attrs", {})
        return bool(status.get("POWERSW", 0))

    async def async_set_native_value(self, value: float) -> None:
        if not self.is_fireplace_on:
            _LOGGER.warning("Fireplace %s is OFF — cannot change %s", self.did, self._key)
            return
        await self.coordinator.async_set_and_refresh(self.did, {self._key: int(value)})
