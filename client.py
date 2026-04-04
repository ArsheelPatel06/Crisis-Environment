"""
Crisis Intelligence Environment - Python Client
"""
import requests
from typing import Dict, Any


class CrisisIntelligenceClient:

    def __init__(self, base_url: str = "http://localhost:7860"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def health(self) -> Dict:
        r = self.session.get(f"{self.base_url}/health", timeout=10)
        r.raise_for_status()
        return r.json()

    def reset(self, difficulty: str = "easy") -> Dict:
        r = self.session.post(
            f"{self.base_url}/reset",
            params={"difficulty": difficulty},
            timeout=10
        )
        r.raise_for_status()
        return r.json()["observation"]

    def step(self, action: Dict[str, Any]):
        r = self.session.post(
            f"{self.base_url}/step",
            json=action,
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        return data["observation"], data["reward"], data["done"], data["info"]

    def state(self) -> Dict:
        r = self.session.get(f"{self.base_url}/state", timeout=10)
        r.raise_for_status()
        return r.json()["state"]
