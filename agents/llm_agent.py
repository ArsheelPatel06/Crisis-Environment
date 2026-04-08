"""
LLM Crisis Agent - Clean Version

Uses LiteLLM proxy for priority assignment with heuristic fallback.
"""

import os
import json
import re
import requests
from typing import Dict, List, Any
from agents.heuristic_agent import HeuristicCrisisAgent


# -------------------- LLM CLIENT --------------------
def get_llm_config():
    return {
        "base_url": os.getenv("API_BASE_URL"),
        "api_key": os.getenv("API_KEY"),
        "model": os.getenv("MODEL_NAME", "gpt-3.5-turbo"),
    }


def build_prompt(incidents: List[Dict[str, Any]], resource_total: int) -> str:
    formatted = "\n".join([
        f"- {inc.get('incident_id', 'UNK')}: "
        f"Severity={inc.get('severity')}, "
        f"People={inc.get('people_affected')}"
        for inc in incidents
    ])

    return f"""
You are a crisis resource allocation expert.

Incidents:
{formatted}

Total resources: {resource_total}

Assign priority (high/medium/low) for each incident.

Return ONLY JSON:
{{"priorities": {{"ID": "high"}}}}
"""


def parse_llm_response(text: str) -> Dict[str, str]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}

    try:
        data = json.loads(match.group())
        priorities = data.get("priorities", {})
        return {
            k: v for k, v in priorities.items()
            if v in ["high", "medium", "low"]
        }
    except:
        return {}


def call_llm(incidents: List[Dict[str, Any]], resource_total: int) -> Dict[str, str]:
    config = get_llm_config()

    if not config["base_url"] or not config["api_key"]:
        print("[LLM] Missing config")
        return {}

    try:
        prompt = build_prompt(incidents, resource_total)

        response = requests.post(
            f"{config['base_url']}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 400,
            },
            timeout=10,
        )

        if response.status_code != 200:
            print("[LLM] HTTP error:", response.status_code)
            return {}

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        parsed = parse_llm_response(content)

        print(f"[LLM] ✓ {len(parsed)} priorities")
        return parsed

    except Exception as e:
        print("[LLM ERROR]:", str(e))
        return {}


# -------------------- AGENT --------------------
class LLMCrisisAgent:
    """LLM-powered agent with heuristic fallback."""

    def __init__(self, api_url: str = "http://localhost:7860"):
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.heuristic = HeuristicCrisisAgent(api_url)

        print("[LLM] Agent initialized")

    def reset(self, difficulty: str = "easy") -> Dict[str, Any]:
        res = self.session.post(f"{self.api_url}/reset", params={"difficulty": difficulty})
        res.raise_for_status()
        return res.json()["observation"]

    def generate_prediction(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        print("[LLM] Generating prediction...")

        input_data = observation.get("input", {})
        incidents = input_data.get("incidents", [])
        resource_total = int(input_data.get("resource_units_total", 0))

        # Step 1: heuristic baseline
        base = self.heuristic.generate_prediction(observation)

        cleaned_data = base["cleaned_data"]
        priorities = base["priorities"]
        allocation = base["allocation"]

        # Step 2: LLM priorities
        print("[LLM] Calling LLM...")
        llm_priorities = call_llm(incidents, resource_total)

        if llm_priorities:
            priorities.update(llm_priorities)
            print("[LLM] Using LLM priorities")
        else:
            print("[LLM] Fallback to heuristic")

        return {
            "cleaned_data": cleaned_data,
            "priorities": priorities,
            "allocation": allocation,
        }

    def run_episode(self, difficulty: str = "easy") -> Dict[str, Any]:
        obs = self.reset(difficulty)
        pred = self.generate_prediction(obs)

        res = self.session.post(f"{self.api_url}/step", json=pred)
        res.raise_for_status()

        result = res.json()

        return {
            "difficulty": difficulty,
            "reward": result.get("reward", 0.0),
            "scores": result.get("info", {}).get("scores", {}),
            "done": result.get("done", False),
        }