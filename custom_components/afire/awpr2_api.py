from __future__ import annotations

import logging
import time
from typing import Any

import requests

from .const import (
    AWPR2_COLOR_COMMANDS,
    AWPR2_COLOR_STATE_MAP,
    AWPR2_COMMAND_DELAY_SECONDS,
    AWPR2_DEFAULT_MODEL,
    AWPR2_EFFECTS,
    AWPR2_IOT_MODELS,
    AWPR2_REFRESH_DELAY_SECONDS,
    COLOR_PRESETS,
    MODEL_PRESTIGE,
    SERIES_AWPR2,
)

_LOGGER = logging.getLogger(__name__)
API_BASE = "https://afire.winhui.com.cn/api/v1"
REQUEST_TIMEOUT = 15


class Awpr2Backend:
    """Backend for the AWPR2 API family."""

    series = SERIES_AWPR2

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.authcode: str | None = None

    def login(self) -> None:
        # AWPR2 uses a different host and returns an auth token in `authcode`
        # instead of the Gizwits token used by the legacy series.
        response = requests.post(
            f"{API_BASE}/commons/login/password",
            data={"tel": self.username, "password": self.password},
            headers={"lang": "en"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        if str(data.get("code")) != "200" or not data.get("authcode"):
            raise RuntimeError(data.get("msg") or "AWPR2 authentication failed")

        self.authcode = str(data["authcode"])

    def ensure_token(self) -> None:
        if not self.authcode:
            self.login()

    def get_devices(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/products")
        products = self._extract_products(payload)
        results: list[dict[str, Any]] = []

        for product in products:
            raw_id = str(product.get("id") or "")
            if not raw_id:
                continue

            iot_id = str(product.get("iotId", ""))
            # Unknown AWPR2 models temporarily default to PRESTIGE until the
            # real iotId -> model mapping is identified from live devices.
            model = AWPR2_IOT_MODELS.get(iot_id, AWPR2_DEFAULT_MODEL)
            attrs = self._parse_open_state(str(product.get("open_state", "")), model)
            supports_rgb = model == MODEL_PRESTIGE

            results.append(
                {
                    "did": f"awpr2:{raw_id}",
                    "backend_id": raw_id,
                    "series": self.series,
                    "model": model,
                    "name": product.get("name", "AFIRE Fireplace"),
                    "mac": product.get("mac", "unknown"),
                    "iotId": iot_id,
                    "state": product.get("state"),
                    "ranges": self._ranges(),
                    "color_presets": COLOR_PRESETS if supports_rgb else {},
                    "effect_commands": AWPR2_EFFECTS if supports_rgb else {},
                    "attrs": attrs,
                    "refresh_delay": AWPR2_REFRESH_DELAY_SECONDS,
                }
            )

        return results

    def get_status(self, device: dict[str, Any]) -> dict[str, Any]:
        payload = self._request("POST", "/Online", params={"id": device["backend_id"]})
        open_state = payload.get("open_state")

        if open_state is None and isinstance(payload.get("data"), dict):
            open_state = payload["data"].get("open_state")

        return self._parse_open_state(str(open_state or ""), device["model"])

    def set_attr(self, device: dict[str, Any], attrs: dict[str, Any]) -> dict[str, Any]:
        current = dict(device.get("attrs", {}))
        # AWPR2 is command-based, so one logical change may translate into
        # multiple virtual key presses plus an optimistic local state update.
        commands, optimistic = self._commands_for_attrs(device, current, attrs)

        for index, command in enumerate(commands):
            self._request("POST", "/operation", params={"id": device["backend_id"], "operation": command})
            if index < len(commands) - 1:
                time.sleep(AWPR2_COMMAND_DELAY_SECONDS)

        return {
            "attrs": optimistic,
            "refresh_delay": AWPR2_REFRESH_DELAY_SECONDS if commands else 0,
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        allow_retry: bool = True,
    ) -> dict[str, Any]:
        self.ensure_token()
        headers = {"token": self.authcode or "", "lang": "en"}
        response = requests.request(
            method,
            f"{API_BASE}{path}",
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        # The AWPR2 API can signal expired auth either via HTTP 401 or inside
        # the JSON payload with code 401, so both cases retry once.
        if response.status_code == 401 and allow_retry:
            self.authcode = None
            self.login()
            return self._request(method, path, params=params, allow_retry=False)

        response.raise_for_status()
        payload = response.json()
        code = str(payload.get("code"))
        if code == "401" and allow_retry:
            self.authcode = None
            self.login()
            return self._request(method, path, params=params, allow_retry=False)
        if code != "200":
            raise RuntimeError(payload.get("msg") or f"AWPR2 request failed for {path}")
        return payload

    def _commands_for_attrs(
        self,
        device: dict[str, Any],
        current: dict[str, Any],
        attrs: dict[str, Any],
    ) -> tuple[list[str], dict[str, Any]]:
        commands: list[str] = []
        optimistic: dict[str, Any] = {}
        supports_rgb = device.get("model") == MODEL_PRESTIGE

        for key, value in attrs.items():
            if key == "POWERSW":
                target = int(value)
                if target != int(current.get("POWERSW", 0)):
                    commands.append("PowON1" if target else "PowON0")
                    optimistic["POWERSW"] = target
            elif key == "LED_SW":
                target = int(value)
                if target != int(current.get("LED_SW", 0)):
                    commands.append("Key8")
                    optimistic["LED_SW"] = target
            elif key == "COLOR_SW" and supports_rgb:
                target = int(value)
                if target != int(current.get("COLOR_SW", 0)):
                    commands.append("Key9")
                    optimistic["COLOR_SW"] = target
                    if not target:
                        optimistic["RGB_PLAY"] = 0
                        for color_key in AWPR2_COLOR_COMMANDS:
                            optimistic[color_key] = 0
            elif key == "RGB_PLAY" and supports_rgb:
                target = int(value)
                if target != int(current.get("RGB_PLAY", 0)):
                    commands.append("KeyA")
                    optimistic["RGB_PLAY"] = target
                    if target:
                        for color_key in AWPR2_COLOR_COMMANDS:
                            optimistic[color_key] = 0
            elif key in {"FLAME", "SPEED", "BRIGHTNESS"}:
                target = int(value)
                current_value = int(current.get(key, target))
                command_up, command_down = {
                    "FLAME": ("Key2", "Key3"),
                    "SPEED": ("Key4", "Key5"),
                    "BRIGHTNESS": ("Key6", "Key7"),
                }[key]
                while current_value < target:
                    commands.append(command_up)
                    current_value += 1
                while current_value > target:
                    commands.append(command_down)
                    current_value -= 1
                optimistic[key] = target
            elif key in AWPR2_COLOR_COMMANDS and supports_rgb:
                commands.append(AWPR2_COLOR_COMMANDS[key])
                optimistic["COLOR_SW"] = 1
                optimistic["RGB_PLAY"] = 0
                for color_key in AWPR2_COLOR_COMMANDS:
                    optimistic[color_key] = 1 if color_key == key else 0

        if "POWERSW" in optimistic and not optimistic["POWERSW"]:
            optimistic["LED_SW"] = 0
            optimistic["COLOR_SW"] = 0
            optimistic["RGB_PLAY"] = 0
            for color_key in AWPR2_COLOR_COMMANDS:
                optimistic[color_key] = 0

        return commands, optimistic

    def _parse_open_state(self, open_state: str, model: str) -> dict[str, Any]:
        # The API returns an 8-character ASCII state string. Bytes 5-7 are the
        # characters '1'..'8' (documented as 0x31..0x38), so they are parsed as
        # decimal digits after extracting each character.
        chars = (open_state or "").strip()
        if len(chars) < 8:
            chars = chars.ljust(8, "0")

        attrs: dict[str, Any] = {
            "POWERSW": 1 if chars[0] == "1" else 0,
            "LED_SW": 1 if chars[1] == "1" else 0,
            "FLAME": self._decode_level(chars[4], default=1),
            "SPEED": self._decode_level(chars[5], default=1),
            "BRIGHTNESS": self._decode_level(chars[6], default=1),
        }

        if model == MODEL_PRESTIGE:
            attrs["COLOR_SW"] = 1 if chars[2] == "1" else 0
            attrs["RGB_PLAY"] = 1 if chars[3] == "1" else 0
            for color_key in AWPR2_COLOR_COMMANDS:
                attrs[color_key] = 0
            selected_color = AWPR2_COLOR_STATE_MAP.get(chars[7].upper())
            if selected_color:
                attrs[selected_color] = 1

        return attrs

    @staticmethod
    def _extract_products(payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            nested = data.get("data")
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
        return []

    @staticmethod
    def _decode_level(value: str, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _ranges() -> dict[str, dict[str, int]]:
        return {
            "FLAME": {"min": 1, "max": 8, "step": 1},
            "SPEED": {"min": 1, "max": 8, "step": 1},
            "BRIGHTNESS": {"min": 1, "max": 8, "step": 1},
        }
