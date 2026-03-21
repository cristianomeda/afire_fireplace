from __future__ import annotations

import logging
from typing import Any

from .awpr2_api import Awpr2Backend
from .awpr_api import AwprBackend

_LOGGER = logging.getLogger(__name__)


class AfireAPI:
    """Facade that merges AWPR and AWPR2 devices for one account."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.devices: list[dict[str, Any]] = []
        self._devices_by_id: dict[str, dict[str, Any]] = {}
        # One AFIRE account can expose fireplaces from both API families.
        self._backends = {
            "awpr": AwprBackend(username, password),
            "awpr2": Awpr2Backend(username, password),
        }
        self._enabled_backends: set[str] = set()

    def login(self) -> None:
        """Authenticate against every supported backend."""
        errors: list[Exception] = []
        self._enabled_backends = set()

        for name, backend in self._backends.items():
            try:
                backend.login()
            except Exception as exc:
                errors.append(exc)
                _LOGGER.debug("AFIRE backend %s login failed: %s", name, exc)
            else:
                self._enabled_backends.add(name)

        if not self._enabled_backends:
            raise errors[-1] if errors else RuntimeError("Unable to authenticate with AFIRE backends")

    def get_devices(self) -> list[dict[str, Any]]:
        """Return the merged device list across AWPR and AWPR2."""
        if not self._enabled_backends:
            self.login()

        devices: list[dict[str, Any]] = []
        errors: list[Exception] = []

        for name, backend in self._backends.items():
            try:
                # Discovery is best-effort per backend so one family can still
                # work even if the other one is unavailable for this account.
                backend_devices = backend.get_devices()
            except Exception as exc:
                errors.append(exc)
                _LOGGER.debug("AFIRE backend %s discovery failed: %s", name, exc)
                continue

            if backend_devices:
                self._enabled_backends.add(name)
                devices.extend(backend_devices)

        if not devices and errors:
            raise errors[-1]

        self.devices = devices
        self._devices_by_id = {device["did"]: device for device in devices}
        return devices

    def get_status(self, did: str) -> dict[str, Any]:
        """Return the normalized status for one merged device."""
        device = self._require_device(did)
        backend = self._backend_for_device(device)
        if device["series"] == backend.series:
            if device["series"] == "AWPR2":
                # AWPR2 parsing depends on model metadata, so the backend
                # receives the whole normalized device instead of only the raw id.
                attrs = backend.get_status(device)
            else:
                attrs = backend.get_status(device["backend_id"])
        else:
            raise RuntimeError(f"Backend mismatch for device {did}")

        device["attrs"] = attrs
        return attrs

    def set_attr(self, did: str, attrs: dict[str, Any]) -> dict[str, Any]:
        """Apply normalized attributes to a merged device."""
        device = self._require_device(did)
        backend = self._backend_for_device(device)
        result = backend.set_attr(device, attrs)
        device["attrs"].update(result.get("attrs", {}))
        return result

    def _require_device(self, did: str) -> dict[str, Any]:
        if did not in self._devices_by_id:
            self.get_devices()
        device = self._devices_by_id.get(did)
        if device is None:
            raise KeyError(f"Unknown AFIRE device id: {did}")
        return device

    def _backend_for_device(self, device: dict[str, Any]):
        if device["did"].startswith("awpr2:"):
            return self._backends["awpr2"]
        return self._backends["awpr"]
