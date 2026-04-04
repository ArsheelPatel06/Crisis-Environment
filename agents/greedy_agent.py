"""
Greedy Crisis Agent - Multiplicative scoring baseline

Uses multiplicative scoring (severity × population) to make resource allocation.
Strong baseline that recognizes both factors matter significantly.
"""

import requests
import json
from typing import Dict, List, Any


class GreedyCrisisAgent:
    """Agent using multiplicative greedy scoring for crisis resource allocation."""

    def __init__(self, api_url: str = "http://localhost:7860"):
        """Initialize the agent with API URL."""
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()

    def reset(self, difficulty: str = "easy") -> Dict[str, Any]:
        """Reset environment and get new task."""
        response = self.session.post(f"{self.api_url}/reset?difficulty={difficulty}")
        response.raise_for_status()
        return response.json()["observation"]

    def _parse_severity(self, val: Any) -> int:
        """Parse severity with multiple format handling."""
        if val is None:
            return 1
        if isinstance(val, int):
            return min(5, max(1, val))
        if isinstance(val, float):
            return min(5, max(1, int(val)))
        if isinstance(val, str):
            # Remove markdown, spaces
            val = val.strip().replace("**", "").replace("*", "").upper()
            # Map text to severity
            if val in ["CRITICAL", "V", "5"]:
                return 5
            elif val in ["HIGH", "IV", "4"]:
                return 4
            elif val in ["MEDIUM", "III", "3"]:
                return 3
            elif val in ["LOW", "II", "2"]:
                return 2
            elif val in ["MINIMAL", "I", "1"]:
                return 1
            # Try to parse as number
            try:
                return min(5, max(1, int(val)))
            except:
                return 1
        return 1

    def _parse_people(self, val: Any) -> int:
        """Parse people_affected with multiple format handling."""
        if val is None:
            return 0
        if isinstance(val, int):
            return max(0, val)
        if isinstance(val, float):
            return max(0, int(val))
        if isinstance(val, str):
            # Remove formatting (commas, "people", etc.)
            val = val.replace(",", "").strip()
            try:
                return max(0, int(float(val)))
            except:
                return 0
        return 0

    def generate_prediction(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate greedy multiplicative scoring prediction."""
        input_data = observation.get("input", {})
        incidents = input_data.get("incidents", [])
        resource_total_raw = input_data.get("resource_units_total", 0)

        # Parse resource total
        if isinstance(resource_total_raw, str):
            resource_total = int(resource_total_raw.replace(",", ""))
        else:
            resource_total = int(resource_total_raw)

        # Extract incident info
        incident_info = []
        for inc in incidents:
            iid = str(inc.get("incident_id", "")).strip() if inc.get("incident_id") else "UNK"
            severity = self._parse_severity(inc.get("severity"))
            people = self._parse_people(inc.get("people_affected"))

            # Multiplicative scoring: severity × (people/100)
            greedy_score = severity * max(1, people / 100)

            incident_info.append({
                "incident_id": iid,
                "severity": severity,
                "people": people,
                "greedy_score": greedy_score,
                "original": inc
            })

        # Sort by greedy score (descending)
        incident_info.sort(key=lambda x: x["greedy_score"], reverse=True)

        # Build cleaned data
        cleaned_data = {}
        for info in incident_info:
            cleaned_data[info["incident_id"]] = {
                "incident_id": info["incident_id"],
                "severity": min(5, max(1, info["severity"])),  # Clamp to 1-5
                "people_affected": max(0, info["people"])
            }

        # Assign priorities based on ranking (top 30% high, middle 40% medium, rest low)
        priorities = {}
        num_incidents = len(incident_info)
        for i, info in enumerate(incident_info):
            if i < num_incidents * 0.3:
                priorities[info["incident_id"]] = "high"
            elif i < num_incidents * 0.7:
                priorities[info["incident_id"]] = "medium"
            else:
                priorities[info["incident_id"]] = "low"

        # Allocate resources proportionally to greedy score
        allocation = {}
        total_score = sum(info["greedy_score"] for info in incident_info)

        if total_score > 0:
            for info in incident_info:
                proportion = info["greedy_score"] / total_score
                allocation[info["incident_id"]] = max(1, int(resource_total * proportion))
        else:
            # Fallback: equal allocation
            per_incident = resource_total // len(incident_info) if incident_info else 0
            for info in incident_info:
                allocation[info["incident_id"]] = per_incident

        return {
            "cleaned_data": cleaned_data,
            "priorities": priorities,
            "allocation": allocation
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
