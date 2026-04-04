"""
Heuristic Crisis Agent - Weighted baseline agent

Uses heuristic rules (0.4×severity + 0.6×population) to make resource allocation.
Provides a strong baseline between random and sophisticated agents.
"""

import requests
import json
from typing import Dict, List, Any


class HeuristicCrisisAgent:
    """Agent using heuristics for crisis resource allocation."""

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
        """Parse severity with mapping-based handling."""
        mapping = {
            "CRITICAL": 5,
            "EXTREME": 4,
            "HIGH": 5,
            "MEDIUM": 3,
            "MODERATE": 3,
            "LOW": 2,
            "MINIMAL": 1,
            "V": 5,
            "IV": 4,
            "III": 3,
            "II": 2,
            "I": 1,
        }

        if val is None or val == "":
            return 3  # Default to MEDIUM if missing

        if isinstance(val, int):
            return min(5, max(1, val))

        if isinstance(val, float):
            return min(5, max(1, int(val)))

        if isinstance(val, str):
            # Clean up the string
            cleaned = val.strip().upper().replace("**", "").replace("*", "")

            # Check mapping
            if cleaned in mapping:
                return mapping[cleaned]

            # Try to parse as number
            if cleaned.isdigit():
                return min(5, max(1, int(cleaned)))

            try:
                return min(5, max(1, int(float(cleaned))))
            except:
                return 3  # Default to MEDIUM

        return 3

    def _parse_people(self, val: Any) -> int:
        """Parse people_affected with robust handling."""
        if not val:
            return 0

        if isinstance(val, int):
            return max(0, val)

        if isinstance(val, float):
            return max(0, int(val))

        if isinstance(val, str):
            # Remove formatting
            cleaned = val.replace(",", "").replace("+", "").replace(" ", "").strip().lower()

            if not cleaned:
                return 0

            # Text-to-number mapping for common words
            text_mapping = {
                "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
                "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
                "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
                "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
            }

            if cleaned in text_mapping:
                return text_mapping[cleaned]

            try:
                return max(0, int(float(cleaned)))
            except:
                return 0

        return 0

    def _assign_priority(self, severity: int, people: int) -> str:
        """
        Assign priority using data-aware rules (not score thresholds).

        Rules prioritize:
        - Huge populations (>3000)
        - High severity + significant people (>=4 and >200)
        - High severity alone (>=4)
        - Moderate populations (>500)
        """
        # Mega-disaster: huge population
        if people > 3000:
            return "high"

        # High severity + many people
        if severity >= 4 and people > 200:
            return "high"

        # High severity alone
        if severity >= 4:
            return "medium"

        # Moderate population
        if people > 500:
            return "medium"

        # Default: low priority
        return "low"

    def generate_prediction(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate optimized prediction using data-aware priority + tier-based allocation.

        Strategy:
        1. Parse incidents carefully (mapping-based severity, robust people parsing)
        2. Assign priority using data-aware rules (population thresholds & severity combos)
        3. Allocate resources tier-based: 65% high, 25% medium, 10% low
        """
        input_data = observation.get("input", {})
        incidents = input_data.get("incidents", [])
        resource_total_raw = input_data.get("resource_units_total", 0)

        # Parse resource total (defensive)
        try:
            if isinstance(resource_total_raw, str):
                resource_total = int(resource_total_raw.replace(",", "").replace("+", ""))
            else:
                resource_total = int(resource_total_raw)
        except (ValueError, TypeError, AttributeError):
            # Fallback: default budget
            resource_total = 50

        # Detect ID prefix from existing incidents (Z, H, etc.)
        prefix = "Z"  # Default
        for inc in incidents:
            iid = inc.get("incident_id")
            if iid and isinstance(iid, str) and len(iid) > 0:
                # Extract alpha prefix (e.g., "H" from "H-01" or "Z" from "Z-05")
                import re
                match = re.match(r"([A-Z]+)", iid.upper())
                if match:
                    prefix = match.group(1)
                    break

        # Extract incident info with improved scoring
        incident_info = []
        for idx, inc in enumerate(incidents):
            # Normalize incident ID: convert to string and uppercase
            raw_id = inc.get("incident_id")
            if raw_id is None or raw_id == "":
                # Generate ID with detected prefix
                iid = f"{prefix}-{str(idx+1).zfill(2)}"
            elif isinstance(raw_id, int):
                # Map numeric IDs to detected prefix format
                iid = f"{prefix}-{str(idx+1).zfill(2)}"
            else:
                iid = str(raw_id).upper().strip()

            severity = self._parse_severity(inc.get("severity"))

            # Parse people with fallback to alternative fields
            people = self._parse_people(inc.get("people_affected"))
            if people == 0 and inc.get("casualties_est"):
                people = self._parse_people(inc.get("casualties_est"))

            # Assign priority using data-aware rules (not score thresholds)
            priority_level = self._assign_priority(severity, people)

            incident_info.append({
                "incident_id": iid,
                "severity": severity,
                "people": people,
                "priority_level": priority_level,
                "original": inc
            })

        # Build cleaned data
        cleaned_data = {}
        for info in incident_info:
            cleaned_data[info["incident_id"]] = {
                "incident_id": info["incident_id"],
                "severity": min(5, max(1, info["severity"])),
                "people_affected": max(0, info["people"])
            }

        # Assign priorities based on score (not ranking)
        priorities = {}
        for info in incident_info:
            priorities[info["incident_id"]] = info["priority_level"]

        # Tier-based allocation with optimized weights: 65% high, 25% medium, 10% low
        # This gives critical incidents more resources
        high_incidents = [info for info in incident_info if info["priority_level"] == "high"]
        medium_incidents = [info for info in incident_info if info["priority_level"] == "medium"]
        low_incidents = [info for info in incident_info if info["priority_level"] == "low"]

        high_budget = int(0.65 * resource_total)
        medium_budget = int(0.25 * resource_total)
        low_budget = resource_total - high_budget - medium_budget

        allocation = {}

        # Distribute high budget
        if high_incidents:
            per_high = high_budget // len(high_incidents)
            for info in high_incidents:
                allocation[info["incident_id"]] = max(1, per_high)

        # Distribute medium budget
        if medium_incidents:
            per_medium = medium_budget // len(medium_incidents)
            for info in medium_incidents:
                allocation[info["incident_id"]] = max(1, per_medium)

        # Distribute low budget
        if low_incidents:
            per_low = low_budget // len(low_incidents)
            for info in low_incidents:
                allocation[info["incident_id"]] = max(1, per_low)

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
