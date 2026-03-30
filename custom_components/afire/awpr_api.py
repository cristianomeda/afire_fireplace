from __future__ import annotations

import logging
import time
from typing import Any

import requests
from requests import Response

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
TRANSIENT_RETRY_DELAY = 1
STATUS_FAILURE_BACKOFF_BASE = 30
STATUS_FAILURE_BACKOFF_MAX = 300
TRANSIENT_EXCEPTIONS = (
    requests.exceptions.ConnectTimeout,
    requests.exceptions.ConnectionError,
    requests.exceptions.ReadTimeout,
    requests.exceptions.SSLError,
)


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
        self.session = requests.Session()
        self._status_cache: dict[str, dict[str, Any]] = {}
        self._status_backoff_until: dict[str, float] = {}
        self._status_failures: dict[str, int] = {}

    def login(self) -> None:
        url = f"{API_BASE}/login"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Gizwits-Application-Id": self.appid,
            "X-Gizwits-User-token": "",
        }
        payload = {"username": self.username, "password": self.password, "lang": "en"}

        response = self.session.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
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
        response = self._request("GET", "/bindings")
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
        now = time.time()
        if raw_id in self._status_cache and now < self._status_backoff_until.get(raw_id, 0):
            return dict(self._status_cache[raw_id])

        try:
            response = self._request("GET", f"/devdata/{raw_id}/latest")
        except TRANSIENT_EXCEPTIONS as exc:
            cached = self._status_cache.get(raw_id)
            if cached is None:
                raise

            failure_count = self._status_failures.get(raw_id, 0) + 1
            self._status_failures[raw_id] = failure_count
            backoff_seconds = min(
                STATUS_FAILURE_BACKOFF_MAX,
                STATUS_FAILURE_BACKOFF_BASE * (2 ** (failure_count - 1)),
            )
            self._status_backoff_until[raw_id] = time.time() + backoff_seconds
            _LOGGER.warning(
                "AWPR status fetch failed for %s, using cached state for %ss: %s",
                raw_id,
                backoff_seconds,
                exc,
            )
            return dict(cached)

        attrs = response.json().get("attr", {}) or {}
        if not isinstance(attrs, dict):
            attrs = {}

        self._status_cache[raw_id] = dict(attrs)
        self._status_failures.pop(raw_id, None)
        self._status_backoff_until.pop(raw_id, None)
        return attrs

    def set_attr(self, device: dict[str, Any], attrs: dict[str, Any]) -> dict[str, Any]:
        self._request("POST", f"/control/{device['backend_id']}", json={"attrs": attrs}, json_request=True)
        return {"attrs": attrs, "refresh_delay": 0}

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        json_request: bool = False,
        retry_auth: bool = True,
        retry_transient: bool = True,
    ) -> Response:
        self.ensure_token()
        headers = {
            "Accept": "application/json",
            "X-Gizwits-Application-Id": self.appid,
            "X-Gizwits-User-token": self.token,
        }
        if json_request:
            headers["Content-Type"] = "application/json"

        try:
            response = self.session.request(
                method,
                f"{API_BASE}{path}",
                headers=headers,
                json=json,
                timeout=REQUEST_TIMEOUT,
            )
        except TRANSIENT_EXCEPTIONS as exc:
            if retry_transient:
                _LOGGER.warning("AWPR request %s failed transiently, retrying once: %s", path, exc)
                self._reset_session()
                time.sleep(TRANSIENT_RETRY_DELAY)
                return self._request(
                    method,
                    path,
                    json=json,
                    json_request=json_request,
                    retry_auth=retry_auth,
                    retry_transient=False,
                )
            raise

        if response.status_code in (401, 403) and retry_auth:
            self.login()
            return self._request(
                method,
                path,
                json=json,
                json_request=json_request,
                retry_auth=False,
                retry_transient=retry_transient,
            )
        if response.status_code != 200:
            _LOGGER.error("AWPR request failed for %s: %s - %s", path, response.status_code, response.text)
            response.raise_for_status()
        return response

    def _reset_session(self) -> None:
        self.session.close()
        self.session = requests.Session()

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
