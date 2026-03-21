from __future__ import annotations

import logging
import time
from typing import Any

import requests

from .const import (
    AWPR_EFFECTS,
    AWPR_PRODUCT_MODELS,
    COLOR_PRESETS,
    DEFAULT_APPID,
    MODEL_ADVANCED,
    SERIES_AWPR,
)

_LOGGER = logging.getLogger(__name__)
API_BASE = "https://api.gizwits.com/app"
REQUEST_TIMEOUT = 15


class AwprBackend:
    """Legacy AWPR backend powered by the Gizwits cloud."""

    series = SERIES_AWPR

    def __init__(self, username: str, password: str, appid: str = DEFAULT_APPID) -> None:
        self.username = username
        self.password = password
        self.appid = appid
        self.token: str | None = None
        self.uid: str | None = None
        self.token_expiry: int = 0

    def login(self) -> None:
        url = f"{API_BASE}/login"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Gizwits-Application-Id": self.appid,
            "X-Gizwits-User-token": "",
        }
        payload = {"username": self.username, "password": self.password, "lang": "en"}

        response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            _LOGGER.error("AWPR login failed: %s - %s", response.status_code, response.text)
            response.raise_for_status()

        data = response.json()
        self.token = data.get("token")
        self.uid = data.get("uid")
        self.token_expiry = int(data.get("expire_at", time.time() + 3600))

    def ensure_token(self) -> None:
        if not self.token or time.time() > (self.token_expiry - 30):
            self.login()

    def get_devices(self) -> list[dict[str, Any]]:
        self.ensure_token()
        headers = {
            "Accept": "application/json",
            "X-Gizwits-Application-Id": self.appid,
            "X-Gizwits-User-token": self.token,
        }
        response = requests.get(f"{API_BASE}/bindings", headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            _LOGGER.error("AWPR get_devices failed: %s - %s", response.status_code, response.text)
            response.raise_for_status()

        devices = response.json().get("devices", [])
        results: list[dict[str, Any]] = []

        for device in devices:
            raw_id = str(device["did"])
            attrs = self.get_status(raw_id)
            product_key = device.get("product_key")
            model = AWPR_PRODUCT_MODELS.get(product_key, MODEL_ADVANCED)
            supports_rgb = "COLOR_SW" in attrs

            results.append(
                {
                    # Legacy AWPR payloads are normalized here so the rest of the
                    # integration can stay backend-agnostic.
                    "did": f"awpr:{raw_id}",
                    "backend_id": raw_id,
                    "series": self.series,
                    "model": model,
                    "name": device.get("product_name", "AFIRE Fireplace"),
                    "mac": device.get("mac", "unknown"),
                    "product_key": product_key,
                    "ranges": self._ranges(attrs),
                    "color_presets": COLOR_PRESETS if supports_rgb else {},
                    "effect_commands": AWPR_EFFECTS if supports_rgb else {},
                    "attrs": attrs,
                    "refresh_delay": 0,
                }
            )

        return results

    def get_status(self, raw_id: str) -> dict[str, Any]:
        self.ensure_token()
        headers = {
            "Accept": "application/json",
            "X-Gizwits-Application-Id": self.appid,
            "X-Gizwits-User-token": self.token,
        }
        response = requests.get(f"{API_BASE}/devdata/{raw_id}/latest", headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            _LOGGER.error("AWPR get_status failed: %s - %s", response.status_code, response.text)
            response.raise_for_status()

        attrs = response.json().get("attr", {}) or {}
        return attrs if isinstance(attrs, dict) else {}

    def set_attr(self, device: dict[str, Any], attrs: dict[str, Any]) -> dict[str, Any]:
        self.ensure_token()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Gizwits-Application-Id": self.appid,
            "X-Gizwits-User-token": self.token,
        }
        response = requests.post(
            f"{API_BASE}/control/{device['backend_id']}",
            headers=headers,
            json={"attrs": attrs},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code != 200:
            _LOGGER.error("AWPR set_attr failed: %s - %s", response.status_code, response.text)
            response.raise_for_status()

        return {"attrs": attrs, "refresh_delay": 0}

    @staticmethod
    def _ranges(attrs: dict[str, Any]) -> dict[str, dict[str, int]]:
        ranges: dict[str, dict[str, int]] = {}
        if "FLAME" in attrs:
            ranges["FLAME"] = {"min": 0, "max": 5, "step": 1}
        if "SPEED" in attrs:
            ranges["SPEED"] = {"min": 0, "max": 5, "step": 1}
        if "BRIGHTNESS" in attrs:
            ranges["BRIGHTNESS"] = {"min": 1, "max": 5, "step": 1}
        return ranges
