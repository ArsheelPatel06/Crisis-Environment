"""
LLM Crisis Agent - Uses LiteLLM proxy for intelligent prioritization

Integrates with OpenAI-compatible API (via LiteLLM proxy) for crisis priority assignment.
Falls back to heuristic logic if LLM is unavailable.

Environment Variables:
  API_BASE_URL: Base URL for LiteLLM proxy (e.g., http://localhost:8000)
  API_KEY: API key for LiteLLM proxy
"""

import os
import requests
import json
from typing import Dict, List, Any
from agents.heuristic_agent import HeuristicCrisisAgent


def call_llm(
    incidents: List[Dict[str, Any]],
    resource_total: int,
    api_base_url: str = None,
    api_key: str = None,
) -> Dict[str, str]:
    """
    Call LiteLLM proxy to get priority assignments for incidents.

    Args:
        incidents: List of incident dictionaries with severity, people_affected
        resource_total: Total resources available for allocation
        api_base_url: Base URL for LiteLLM proxy (env: API_BASE_URL)
        api_key: API key for LiteLLM proxy (env: API_KEY)

    Returns:
        dict: {incident_id: priority_level} where priority_level is "high", "medium", or "low"
        Returns {} if LLM call fails (caller should fallback to heuristic)
    """
    # Get environment variables if not provided
    api_base_url = api_base_url or os.getenv("API_BASE_URL")
    api_key = api_key or os.getenv("API_KEY")

    if not api_base_url or not api_key:
        print("[LLM] Missing API_BASE_URL or API_KEY - will skip LLM call")
        return {}

    try:
        print(f"[LLM] Calling LiteLLM proxy at {api_base_url}")

        # Format incidents for LLM prompt
        incidents_text = ""
        for inc in incidents:
            iid = inc.get("incident_id", "UNKNOWN")
            severity = inc.get("severity", "N/A")
            people = inc.get("people_affected", 0)
            desc = inc.get("description", "")[:100]
            incidents_text += f"- {iid}: Severity={severity}, People={people}, Description={desc}\n"

        # Create prompt for LLM
        prompt = f"""You are an expert crisis resource allocation specialist. Analyze these disaster incidents and assign priority levels (high/medium/low) based on severity and people affected.

Incidents:
{incidents_text}

Total resources available: {resource_total} units

For each incident, determine if it should be prioritized as:
- HIGH: Critical impact, severe consequences if not addressed
- MEDIUM: Moderate impact, important but not critical
- LOW: Minor impact, can be addressed later

Return ONLY valid JSON in this exact format (no other text):
{{"priorities": {{"INCIDENT_ID": "high", "INCIDENT_ID2": "medium", ...}}}}
"""

        # Call LiteLLM proxy with OpenAI-compatible format
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": "gpt-3.5-turbo",  # Will be routed by LiteLLM
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500,
        }

        response = requests.post(
            f"{api_base_url}/v1/chat/completions",
            json=data,
            headers=headers,
            timeout=10,
        )

        if response.status_code != 200:
            print(f"[LLM] Error: HTTP {response.status_code}")
            print(f"[LLM] Response: {response.text[:200]}")
            return {}

        result = response.json()

        # Extract message content
        if "choices" not in result or len(result["choices"]) == 0:
            print("[LLM] Error: No choices in response")
            return {}

        message_content = result["choices"][0].get("message", {}).get("content", "")

        # Parse JSON from response
        import re
        json_match = re.search(r'\{.*\}', message_content, re.DOTALL)
        if not json_match:
            print("[LLM] Error: Could not extract JSON from response")
            return {}

        parsed = json.loads(json_match.group())
        priorities = parsed.get("priorities", {})

        # Validate priorities
        valid_priorities = {}
        for iid, priority in priorities.items():
            if priority in ["high", "medium", "low"]:
                valid_priorities[iid] = priority
            else:
                print(f"[LLM] Ignoring invalid priority '{priority}' for {iid}")

        print(f"[LLM] ✓ Successfully got priorities for {len(valid_priorities)} incidents")
        return valid_priorities

    except requests.exceptions.Timeout:
        print("[LLM] Error: Request timeout (10s)")
        return {}
    except requests.exceptions.ConnectionError:
        print(f"[LLM] Error: Cannot connect to {api_base_url}")
        return {}
    except json.JSONDecodeError as e:
        print(f"[LLM] Error: Invalid JSON in response: {str(e)}")
        return {}
    except Exception as e:
        print(f"[LLM] Error: {str(e)}")
        return {}


class LLMCrisisAgent:
    """Agent using LLM for intelligent crisis resource allocation with heuristic fallback."""

    def __init__(self, api_url: str = "http://localhost:7860"):
        """Initialize the agent with API URL and heuristic fallback."""
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.heuristic = HeuristicCrisisAgent(api_url)
        print("[LLM] LLMCrisisAgent initialized with heuristic fallback")

    def reset(self, difficulty: str = "easy") -> Dict[str, Any]:
        """Reset environment and get new task."""
        response = self.session.post(f"{self.api_url}/reset?difficulty={difficulty}")
        response.raise_for_status()
        return response.json()["observation"]

    def generate_prediction(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate prediction using LLM for priorities, heuristic for cleaning & allocation.

        Strategy:
        1. Clean data using heuristic parser (proven robust)
        2. Get priorities from LLM (intelligent decision making)
        3. If LLM fails, fall back to heuristic priorities
        4. Allocate resources tier-based (heuristic proven strategy)
        """
        print("[LLM] Generating prediction...")

        input_data = observation.get("input", {})
        incidents = input_data.get("incidents", [])
        resource_total_raw = input_data.get("resource_units_total", 0)

        # Step 1: Use heuristic for cleaning & parsing (it's robust)
        heuristic_prediction = self.heuristic.generate_prediction(observation)
        cleaned_data = heuristic_prediction["cleaned_data"]
        heuristic_priorities = heuristic_prediction["priorities"]

        # Step 2: Try to get priorities from LLM
        print("[LLM] Attempting LLM call for priority assignment...")
        llm_priorities = call_llm(incidents, int(resource_total_raw))

        # Step 3: Use LLM priorities if available, otherwise use heuristic
        if llm_priorities:
            print(f"[LLM] Using LLM priorities for {len(llm_priorities)} incidents")
            # Merge: LLM for available incidents, heuristic for others
            priorities = {**heuristic_priorities}  # Start with heuristic
            priorities.update(llm_priorities)  # Override with LLM
            print(f"[LLM] Final priorities: {priorities}")
        else:
            print("[LLM] LLM failed, falling back to heuristic priorities")
            priorities = heuristic_priorities

        # Step 4: Use heuristic allocation strategy (proven effective)
        allocation = heuristic_prediction["allocation"]

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
