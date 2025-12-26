from __future__ import annotations
import os, requests

API_BASE = os.environ.get("API_BASE", "http://hakilix-api:8080/v1")

class Api:
    def __init__(self, token: str | None):
        self.token = token

    def _h(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def login(self, email: str, password: str) -> str:
        r = requests.post(f"{API_BASE}/auth/token", data={"username": email, "password": password}, timeout=6)
        r.raise_for_status()
        return r.json()["access_token"]

    def residents(self):
        r = requests.get(f"{API_BASE}/residents", headers=self._h(), timeout=6); r.raise_for_status(); return r.json()

    def resident_upsert(self, rid: str, name: str):
        r = requests.post(f"{API_BASE}/residents", json={"id": rid, "display_name": name}, headers=self._h(), timeout=8); r.raise_for_status(); return r.json()

    def resident_delete(self, rid: str):
        r = requests.delete(f"{API_BASE}/residents/{rid}", headers=self._h(), timeout=8); r.raise_for_status(); return r.json()

    def latest(self, rid: str):
        r = requests.get(f"{API_BASE}/residents/{rid}/latest", headers=self._h(), timeout=8); r.raise_for_status(); return r.json()

    def tele_recent(self, rid: str):
        r = requests.get(f"{API_BASE}/telemetry/{rid}/recent?limit=180", headers=self._h(), timeout=8); r.raise_for_status(); return r.json()
