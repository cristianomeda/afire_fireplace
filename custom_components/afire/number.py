from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NUMBER_SPECS
from .coordinator import AfireCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: AfireCoordinator = data["coordinator"]

    entities: list[AfireNumber] = []
    for did, dev in coordinator.data.items():
        attrs = dev.get("attrs", {})
        ranges = dev.get("ranges", {})
        for key, spec in NUMBER_SPECS.items():
            if key in attrs:
                range_spec = ranges.get(key, {})
                entities.append(
                    AfireNumber(
                        coordinator,
                        did,
                        dev,
                        spec["label"],
                        key,
                        range_spec.get("min", spec["min"]),
                        range_spec.get("max", spec["max"]),
                        range_spec.get("step", spec["step"]),
                        spec["icon"],
                    )
                )
    async_add_entities(entities)


class AfireNumber(CoordinatorEntity, NumberEntity):
    def __init__(
        self,
        coordinator: AfireCoordinator,
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
        self.did = did
        self.dev = dev
        self._key = key

        base_name = dev.get("name", "Fireplace")
        if isinstance(base_name, str) and base_name.upper() == "AFIRE":
            base_name = "Fireplace"
        self._attr_name = f"{base_name} {label}"

        self._attr_unique_id = f"{did.replace(':', '_')}_{key.lower()}"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_icon = icon

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
            _LOGGER.warning("Fireplace %s is OFF - cannot change %s", self.did, self._key)
            return
        await self.coordinator.async_set_device_attrs(self.did, {self._key: int(value)})
