"""Unofficial Econergy cloud API client."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

BASE_URL = "https://raegy28bl9.execute-api.eu-west-3.amazonaws.com/Prod"


class EconergyError(Exception):
    """Base Econergy API error."""


class EconergyAuthError(EconergyError):
    """Authentication failed."""


class EconergyConnectionError(EconergyError):
    """Connection to Econergy failed."""


class EconergyApi:
    """Client for the Econergy cloud API used by the Econergy application."""

    def __init__(self, email: str, password: str) -> None:
        self.email = email
        self.password = password
        self.token = None
        self.home_id = None

    def authenticate(self):
        payload = json.dumps({
            "email": self.email,
            "password": self.password,
            "agent": "ECONERGY_APP",
            "version": "1.0.0",
        }).encode()

        req = urllib.request.Request(
            BASE_URL + "/auth",
            data=payload,
            method="PUT",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode())
        except urllib.error.HTTPError as err:
            if err.code in (401, 403):
                raise EconergyAuthError("Econergy authentication failed") from err
            raise EconergyConnectionError(f"Econergy HTTP error: {err.code}") from err
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            raise EconergyConnectionError("Unable to connect to Econergy") from err

        if data.get("status") != "OK" or not data.get("result"):
            raise EconergyAuthError("Econergy authentication failed")

        result = data["result"]
        self.token = result["token"]
        self.home_id = result["homeId"]
        return result

    def _headers(self):
        return {
            "x-session": self.token,
            "x-app-version": "1.0.0",
            "Content-Type": "application/json",
        }

    def _request(self, url, method="GET", data=None, retry=True):
        if not self.token:
            self.authenticate()

        payload = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(
            url, data=payload, method=method, headers=self._headers()
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as err:
            if err.code in (401, 403) and retry:
                self.authenticate()
                return self._request(url, method=method, data=data, retry=False)
            raise EconergyConnectionError(f"Econergy HTTP error: {err.code}") from err
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            raise EconergyConnectionError("Unable to connect to Econergy") from err

    def get_home(self):
        result = self._request(f"{BASE_URL}/v2/homes/{self.home_id}")
        return result["result"]

    def get_device(self, device_id):
        result = self._request(
            f"{BASE_URL}/devices/{device_id}?homeId={self.home_id}"
        )
        return result["result"]

    def set_config(self, device_id, config):
        return self._request(
            f"{BASE_URL}/devices/{device_id}/config",
            method="PUT",
            data=config,
        )

    def set_programs(self, device_id, programs):
        device = self.get_device(device_id)
        config = device["config"].copy()
        config["programs"] = programs
        return self.set_config(device_id, config)
