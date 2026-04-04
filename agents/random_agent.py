"""
Random Crisis Agent - Baseline control agent

Makes random predictions for crisis resource allocation.
Used as a control to compare against more sophisticated agents.
"""

import random
import requests
import json
from typing import Dict, List, Any


class RandomCrisisAgent:
    """Baseline random agent for crisis resource allocation."""

    def __init__(self, api_url: str = "http://localhost:7860"):
        """Initialize the agent with API URL."""
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()

    def reset(self, difficulty: str = "easy") -> Dict[str, Any]:
        """Reset environment and get new task."""
        response = self.session.post(f"{self.api_url}/reset?difficulty={difficulty}")
        response.raise_for_status()
        return response.json()["observation"]

    def generate_prediction(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate random prediction."""
        input_data = observation.get("input", {})
        incidents = input_data.get("incidents", [])
        resource_total = int(input_data.get("resource_units_total", 100))

        # Random cleaning: just copy incident structure
        cleaned_data = {}
        priorities = {}
        allocation = {}

        for inc in incidents:
            iid = str(inc.get("incident_id", "UNK")).strip()

            cleaned_data[iid] = {
                "incident_id": iid,
                "severity": random.randint(1, 5),
                "people_affected": random.randint(0, 10000),
            }

            priorities[iid] = random.choice(["high", "medium", "low"])

        # Random allocation
        remaining = resource_total
        for iid in cleaned_data.keys():
            if iid == list(cleaned_data.keys())[-1]:
                allocation[iid] = remaining
            else:
                alloc = random.randint(0, remaining)
                allocation[iid] = alloc
                remaining -= alloc

        return {
            "cleaned_data": cleaned_data,
            "priorities": priorities,
            "allocation": allocation,
        }

    def run_episode(self, difficulty: str = "easy") -> Dict[str, Any]:
        """Run one complete episode."""
        observation = self.reset(difficulty=difficulty)
        prediction = self.generate_prediction(observation)

        response = self.session.post(
            f"{self.api_url}/step",
            json=prediction,
        )
        response.raise_for_status()

        result = response.json()
        return {
            "difficulty": difficulty,
            "reward": result.get("reward", 0.0),
            "scores": result.get("info", {}).get("scores", {}),
            "done": result.get("done", False),
        }
