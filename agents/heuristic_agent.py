"""
Heuristic Crisis Agent - Weighted baseline agent
"""

import requests
import json
import os
from typing import Dict, List, Any


class HeuristicCrisisAgent:
    """Agent using heuristics + optional LLM validation."""

    def __init__(self, api_url: str = "http://localhost:7860"):
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()

    def reset(self, difficulty: str = "easy") -> Dict[str, Any]:
        response = self.session.post(f"{self.api_url}/reset?difficulty={difficulty}")
        response.raise_for_status()
        return response.json()["observation"]

    # -------------------- LLM CALL (IMPORTANT FOR PHASE 2) --------------------
    def call_llm(self, incidents):
        try:
            from openai import OpenAI
            import os

            base_url = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
            api_key = os.getenv("HF_TOKEN")

            if not api_key:
                print("[LLM] Missing HF_TOKEN")
                return

            client = OpenAI(
                base_url=base_url,
                api_key=api_key,
            )

            response = client.chat.completions.create(
                model=os.getenv("MODEL_NAME", "gpt-4.1-mini"),
                messages=[
                    {
                        "role": "user",
                        "content": f"Analyze these incidents briefly: {incidents[:2]}"
                    }
                ],
                max_tokens=20,
            )

            print("[LLM] SUCCESS:", response.choices[0].message.content)

        except Exception as e:
            print("[LLM] ERROR:", str(e))

    # -------------------- PARSERS --------------------
    def _parse_severity(self, val: Any) -> int:
        mapping = {
            "CRITICAL": 5, "EXTREME": 4, "HIGH": 5,
            "MEDIUM": 3, "MODERATE": 3,
            "LOW": 2, "MINIMAL": 1,
            "V": 5, "IV": 4, "III": 3, "II": 2, "I": 1,
        }

        if val is None:
            return 3

        if isinstance(val, (int, float)):
            return min(5, max(1, int(val)))

        if isinstance(val, str):
            cleaned = val.strip().upper()
            if cleaned in mapping:
                return mapping[cleaned]
            if cleaned.isdigit():
                return int(cleaned)

        return 3

    def _parse_people(self, val: Any) -> int:
        if not val:
            return 0

        try:
            if isinstance(val, str):
                val = val.replace(",", "").strip()
            return max(0, int(float(val)))
        except:
            return 0

    def _assign_priority(self, severity: int, people: int) -> str:
        if people > 3000:
            return "high"
        if severity >= 4 and people > 200:
            return "high"
        if severity >= 4:
            return "medium"
        if people > 500:
            return "medium"
        return "low"

    # -------------------- MAIN LOGIC --------------------
    def generate_prediction(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        input_data = observation.get("input", {})
        incidents = input_data.get("incidents", [])
        resource_total = int(input_data.get("resource_units_total", 50))

        # ✅ IMPORTANT: MAKE LLM CALL HERE
        self.call_llm(incidents)

        incident_info = []

        for idx, inc in enumerate(incidents):
            iid = str(inc.get("incident_id", f"Z-{idx+1}")).upper()
            severity = self._parse_severity(inc.get("severity"))
            people = self._parse_people(inc.get("people_affected"))

            priority = self._assign_priority(severity, people)

            incident_info.append({
                "incident_id": iid,
                "severity": severity,
                "people": people,
                "priority": priority
            })

        cleaned_data = {
            i["incident_id"]: {
                "severity": i["severity"],
                "people_affected": i["people"]
            }
            for i in incident_info
        }

        priorities = {
            i["incident_id"]: i["priority"]
            for i in incident_info
        }

        allocation = {}
        per_incident = max(1, resource_total // max(1, len(incident_info)))

        for i in incident_info:
            allocation[i["incident_id"]] = per_incident

        return {
            "cleaned_data": cleaned_data,
            "priorities": priorities,
            "allocation": allocation
        }

    # -------------------- RUN --------------------
    def run_episode(self, difficulty: str = "easy") -> Dict[str, Any]:
        observation = self.reset(difficulty)
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