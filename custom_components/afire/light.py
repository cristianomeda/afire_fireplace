from __future__ import annotations

import logging
from homeassistant.components.light import (
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AfireCoordinator

_LOGGER = logging.getLogger(__name__)

COLOR_PRESETS = {
    # Reds
    "Red 1": ("RED_KEY1", (198, 50, 38)),
    "Red 2": ("RED_KEY2", (232, 61, 42)),
    "Red 3": ("RED_KEY3", (232, 89, 21)),
    "Red 4": ("RED_KEY4", (232, 154, 41)),
    "Red 5": ("RED_KEY5", (249, 234, 37)),
    # Greens
    "Green 1": ("GREEN_KEY1", (99, 152, 74)),
    "Green 2": ("GREEN_KEY2", (168, 201, 65)),
    "Green 3": ("GREEN_KEY3", (144, 182, 164)),
    "Green 4": ("GREEN_KEY4", (125, 174, 190)),
    "Green 5": ("GREEN_KEY5", (90, 159, 218)),
    # Blues
    "Blue 1": ("BLUE_KEY1", (88, 85, 132)),
    "Blue 2": ("BLUE_KEY2", (108, 110, 173)),
    "Blue 3": ("BLUE_KEY3", (117, 78, 107)),
    "Blue 4": ("BLUE_KEY4", (168, 99, 122)),
    "Blue 5": ("BLUE_KEY5", (196, 103, 144)),
}

# Keys that must always be sent as 0 (toggle-style)
EFFECT_ONLY = {
    "Smooth": "KEY_SMOOTH",
    "Fade 1": "KEY_FADE1",
    "Fade 2": "KEY_FADE2",
}


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: AfireCoordinator = data["coordinator"]
    api = data["api"]

    entities: list[AfireColorLight] = []
    for did, dev in coordinator.data.items():
        attrs = dev.get("attrs", {})
        if "COLOR_SW" in attrs:
            entities.append(AfireColorLight(coordinator, api, did, dev))
    async_add_entities(entities)


class AfireColorLight(CoordinatorEntity, LightEntity):
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = list(EFFECT_ONLY.keys())
    _attr_icon = "mdi:lightbulb-multiple"

    def __init__(self, coordinator: AfireCoordinator, api, did: str, dev: dict):
        super().__init__(coordinator)
        self.api = api
        self.did = did
        self.dev = dev

        base_name = dev.get("alias") or dev.get("name", "Fireplace")
        if base_name.upper() == "AFIRE":
            base_name = "Fireplace"
        self._attr_name = f"{base_name} Colors"

        self._attr_unique_id = f"{did.lower()}_color"
        self._current_effect: str | None = None
        self._current_color: tuple[int, int, int] | None = None

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
        return bool(status.get("COLOR_SW", 0))

    @property
    def effect(self) -> str | None:
        return self._current_effect

    @property
    def rgb_color(self):
        return self._current_color

    @property
    def is_fireplace_on(self) -> bool:
        status = self.coordinator.data.get(self.did, {}).get("attrs", {})
        return bool(status.get("POWERSW", 0))

    async def async_turn_on(self, **kwargs):
        if not self.is_fireplace_on:
            _LOGGER.warning("Fireplace %s is OFF — cannot set color/effect", self.did)
            return

        # COLOR_SW is toggle style → always 0
        await self.coordinator.async_set_and_refresh(self.did, {"COLOR_SW": 0})

        if "rgb_color" in kwargs:
            rgb = kwargs["rgb_color"]
            option = min(
                COLOR_PRESETS.keys(),
                key=lambda o: (COLOR_PRESETS[o][1][0] - rgb[0]) ** 2
                              + (COLOR_PRESETS[o][1][1] - rgb[1]) ** 2
                              + (COLOR_PRESETS[o][1][2] - rgb[2]) ** 2
            )
            key, color = COLOR_PRESETS[option]
            await self.coordinator.async_set_and_refresh(self.did, {key: 1})
            self._current_color = color
            self._current_effect = None

        if "effect" in kwargs and kwargs["effect"] in EFFECT_ONLY:
            key = EFFECT_ONLY[kwargs["effect"]]
            await self.coordinator.async_set_and_refresh(self.did, {key: 0})
            self._current_effect = kwargs["effect"]
            self._current_color = None

    async def async_turn_off(self, **kwargs):
        # COLOR_SW toggle → still 0
        await self.coordinator.async_set_and_refresh(self.did, {"COLOR_SW": 0})
        self._current_color = None
        self._current_effect = None

    async def async_set_effect(self, effect: str) -> None:
        if not self.is_fireplace_on:
            _LOGGER.warning("Fireplace %s is OFF — cannot set effect", self.did)
            return
        if effect in EFFECT_ONLY:
            await self.coordinator.async_set_and_refresh(self.did, {EFFECT_ONLY[effect]: 0})
            self._current_effect = effect
            self._current_color = None
