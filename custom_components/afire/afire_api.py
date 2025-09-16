import logging
import time
from typing import Dict, List

import requests

from .const import DEFAULT_APPID, PRODUCT_MODELS

_LOGGER = logging.getLogger(__name__)
API_BASE = "https://api.gizwits.com/app"


class AfireAPI:
    """Wrapper for AFIRE fireplaces via Gizwits Cloud."""

    def __init__(self, username: str, password: str, appid: str = DEFAULT_APPID) -> None:
        self.username = username
        self.password = password
        self.appid = appid
        self.token: str | None = None
        self.uid: str | None = None
        self.token_expiry: int = 0
        self.devices: List[Dict] = []

    # ---------- Authentication ----------

    def login(self) -> None:
        """Authenticate and store token & expiry."""
        url = f"{API_BASE}/login"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Gizwits-Application-Id": self.appid,
            "X-Gizwits-User-token": ""
        }
        payload = {"username": self.username, "password": self.password, "lang": "en"}

        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code != 200:
            _LOGGER.error("AFIRE login failed: %s - %s", resp.status_code, resp.text)
            resp.raise_for_status()

        data = resp.json()
        self.token = data.get("token")
        self.uid = data.get("uid")
        self.token_expiry = int(data.get("expire_at", time.time() + 3600))
        _LOGGER.info("AFIRE login success (uid=%s, expires=%s)", self.uid, self.token_expiry)

    def ensure_token(self) -> None:
        """Ensure we have a valid token before making API calls."""
        if not self.token or time.time() > (self.token_expiry - 30):
            self.login()

    # ---------- Device discovery ----------

    def get_devices(self) -> List[Dict]:
        """Fetch all fireplaces linked to this account."""
        self.ensure_token()
        headers = {
            "Accept": "application/json",
            "X-Gizwits-Application-Id": self.appid,
            "X-Gizwits-User-token": self.token
        }
        resp = requests.get(f"{API_BASE}/bindings", headers=headers, timeout=15)
        if resp.status_code != 200:
            _LOGGER.error("AFIRE get_devices failed: %s - %s", resp.status_code, resp.text)
            resp.raise_for_status()

        devices = resp.json().get("devices", [])
        results: List[Dict] = []

        for dev in devices:
            did = dev["did"]
            attrs = self.get_status(did)
            product_key = dev.get("product_key")

            # Map to Prestige / Advance
            if product_key in PRODUCT_MODELS:
                model = PRODUCT_MODELS[product_key]
            else:
                model = "ADVANCE"

            results.append({
                "did": did,
                "name": dev.get("product_name", "AFIRE Fireplace"),
                "mac": dev.get("mac", "unknown"),
                "product_key": product_key,
                "model": model,
                "attrs": attrs,
            })

            _LOGGER.info(
                "AFIRE discovered: %s (%s, model=%s, product_key=%s)",
                dev.get("product_name"), did, model, product_key
            )

        self.devices = results
        return results

    # ---------- Device status ----------

    def get_status(self, did: str) -> Dict:
        """Return current attributes of a device."""
        self.ensure_token()
        headers = {
            "Accept": "application/json",
            "X-Gizwits-Application-Id": self.appid,
            "X-Gizwits-User-token": self.token
        }
        url = f"{API_BASE}/devdata/{did}/latest"
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            _LOGGER.error("AFIRE get_status failed: %s - %s", resp.status_code, resp.text)
            resp.raise_for_status()
        return resp.json().get("attr", {}) or {}

    # ---------- Device control ----------

    def set_attr(self, did: str, attrs: Dict) -> Dict:
        """Send control command to a device."""
        self.ensure_token()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Gizwits-Application-Id": self.appid,
            "X-Gizwits-User-token": self.token
        }
        url = f"{API_BASE}/control/{did}"
        resp = requests.post(url, headers=headers, json={"attrs": attrs}, timeout=15)
        if resp.status_code != 200:
            _LOGGER.error("AFIRE set_attr failed: %s - %s", resp.status_code, resp.text)
            resp.raise_for_status()
        return resp.json()
