from __future__ import annotations

import logging

from homeassistant.components.light import ColorMode, LightEntity, LightEntityFeature
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COLOR_PRESETS, DOMAIN
from .coordinator import AfireCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: AfireCoordinator = data["coordinator"]

    entities: list[AfireColorLight] = []
    for did, dev in coordinator.data.items():
        attrs = dev.get("attrs", {})
        if "COLOR_SW" in attrs:
            entities.append(AfireColorLight(coordinator, did, dev))
    async_add_entities(entities)


class AfireColorLight(CoordinatorEntity, LightEntity):
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_icon = "mdi:lightbulb-multiple"
    _attr_color_mode = ColorMode.RGB

    def __init__(self, coordinator: AfireCoordinator, did: str, dev: dict):
        super().__init__(coordinator)
        self.did = did
        self.dev = dev

        base_name = dev.get("name", "Fireplace")
        if isinstance(base_name, str) and base_name.upper() == "AFIRE":
            base_name = "Fireplace"
        self._attr_name = f"{base_name} Colors"
        self._attr_unique_id = f"{did.replace(':', '_')}_color"

        self._effect_commands = dict(dev.get("effect_commands", {}))
        self._color_presets = dict(dev.get("color_presets", COLOR_PRESETS))
        self._attr_effect_list = list(self._effect_commands.keys())
        self._current_effect: str | None = None
        self._current_color: tuple[int, int, int] | None = None
        self._sync_from_status()

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
    def color_mode(self) -> ColorMode:
        return ColorMode.RGB

    @property
    def is_fireplace_on(self) -> bool:
        status = self.coordinator.data.get(self.did, {}).get("attrs", {})
        return bool(status.get("POWERSW", 0))

    async def async_turn_on(self, **kwargs):
        if not self.is_fireplace_on:
            _LOGGER.warning("Fireplace %s is OFF - cannot set color/effect", self.did)
            return

        attrs: dict[str, int] = {}
        if not self.is_on:
            attrs["COLOR_SW"] = 1

        if "rgb_color" in kwargs and self._color_presets:
            preset_name, command, preset_rgb = self._nearest_color_preset(kwargs["rgb_color"])
            attrs[command] = 1
            self._current_color = preset_rgb
            self._current_effect = None
            _LOGGER.debug("Approximating %s with preset %s", kwargs["rgb_color"], preset_name)

        if "effect" in kwargs and kwargs["effect"] in self._effect_commands:
            command = self._effect_commands[kwargs["effect"]]
            attrs[command] = 1
            self._current_effect = kwargs["effect"]
            self._current_color = None

        if not attrs:
            attrs["COLOR_SW"] = 1

        await self.coordinator.async_set_device_attrs(self.did, attrs)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_set_device_attrs(self.did, {"COLOR_SW": 0})
        self._current_color = None
        self._current_effect = None
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sync_from_status()
        super()._handle_coordinator_update()

    def _sync_from_status(self) -> None:
        status = self.coordinator.data.get(self.did, {}).get("attrs", {})
        if not bool(status.get("COLOR_SW", 0)):
            self._current_effect = None
            self._current_color = None
            return

        for effect_name, command in self._effect_commands.items():
            if status.get(command):
                self._current_effect = effect_name
                self._current_color = None
                return

        for _, (command, preset_rgb) in self._color_presets.items():
            if status.get(command):
                self._current_effect = None
                self._current_color = preset_rgb
                return

        self._current_effect = None
        self._current_color = None

    def _nearest_color_preset(
        self, rgb_color: tuple[int, int, int]
    ) -> tuple[str, str, tuple[int, int, int]]:
        requested = tuple(int(channel) for channel in rgb_color)
        # Both backends expose preset color commands rather than true RGB writes,
        # so arbitrary Home Assistant colors are approximated to the nearest
        # supported fireplace preset.
        return min(
            (
                (name, command, preset_rgb)
                for name, (command, preset_rgb) in self._color_presets.items()
            ),
            key=lambda item: sum((requested[index] - item[2][index]) ** 2 for index in range(3)),
        )
