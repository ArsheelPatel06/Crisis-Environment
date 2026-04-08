"""
Crisis Intelligence Environment - Baseline Inference Script
Uses OpenAI Client with evaluator-injected API_BASE_URL and API_KEY.

Required env vars (injected by evaluator):
  API_BASE_URL   - LLM proxy endpoint
  API_KEY        - API key for the proxy
  MODEL_NAME     - model identifier (optional)
  ENV_BASE_URL   - environment server URL (optional, default localhost)
"""

import sys
import os
import json
import re
import requests
from openai import OpenAI

print(f"[INFO] Python version: {sys.version}", flush=True)

API_BASE_URL = os.environ["API_BASE_URL"]
API_KEY = os.environ["API_KEY"]
MODEL_NAME = os.environ.get("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")
ENV_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")
BENCHMARK = "crisis-intelligence-env"

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

SYSTEM_PROMPT = """You are a crisis resource allocation AI agent.
Return ONLY valid JSON with no explanation or markdown.

Phase 1 - clean corrupted data:
{"cleaned_data": {"INC-001": {"incident_id": "INC-001", "severity": 5, "people_affected": 800}}}

Phase 2 - assign priorities (high/medium/low):
{"priorities": {"INC-001": "high", "INC-002": "medium", "INC-003": "low"}}

Phase 3 - allocate integer resources summing to total:
{"allocation": {"INC-001": 25, "INC-002": 15, "INC-003": 10}}

Rules: severity=integer 1-5, people_affected=integer, priorities=high/medium/low, allocation=integers"""


def call_llm(user_msg: str) -> dict:
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
        max_tokens=600,
    )
    text = (completion.choices[0].message.content or "").strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)


def run_task(difficulty: str) -> dict:
    task_name = f"crisis-{difficulty}"
    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    total_reward = 0.0
    steps_taken = 0

    try:
        res = requests.post(f"{ENV_URL}/reset", params={"difficulty": difficulty}, timeout=15)
        res.raise_for_status()
        obs = res.json()["observation"]
        input_data = obs["input"]
        incidents = input_data.get("incidents", [])
        resource_total = input_data.get("resource_units_total", 50)

        # Phase 1: clean data
        steps_taken += 1
        msg1 = f"Phase 1: Clean this corrupted incident data. Resource total: {resource_total}\nIncidents: {json.dumps(incidents)}\nReturn cleaned_data JSON. severity=integer 1-5, people_affected=integer."
        action1 = call_llm(msg1)
        res = requests.post(f"{ENV_URL}/step", json=action1, timeout=15)
        res.raise_for_status()
        r = res.json()
        r1, done = r["reward"], r["done"]
        total_reward += r1
        obs = r["observation"]
        print(f"[STEP] step={steps_taken} action=clean_data reward={r1:.2f} done={str(done).lower()} error=null", flush=True)

        # Phase 2: priorities
        steps_taken += 1
        msg2 = f"Phase 2: Assign priorities. Incidents: {json.dumps(incidents)}\nReturn priorities JSON with high, medium, or low for each incident_id."
        action2 = call_llm(msg2)
        res = requests.post(f"{ENV_URL}/step", json=action2, timeout=15)
        res.raise_for_status()
        r = res.json()
        r2, done = r["reward"], r["done"]
        total_reward += r2
        obs = r["observation"]
        print(f"[STEP] step={steps_taken} action=assign_priorities reward={r2:.2f} done={str(done).lower()} error=null", flush=True)

        # Phase 3: allocation
        steps_taken += 1
        msg3 = f"Phase 3: Allocate exactly {resource_total} resource units. Incidents: {json.dumps(incidents)}\nReturn allocation JSON with integers summing to {resource_total}."
        action3 = call_llm(msg3)
        res = requests.post(f"{ENV_URL}/step", json=action3, timeout=15)
        res.raise_for_status()
        r = res.json()
        r3, done = r["reward"], r["done"]
        total_reward += r3
        print(f"[STEP] step={steps_taken} action=allocate_resources reward={r3:.2f} done={str(done).lower()} error=null", flush=True)

        success = done and total_reward > 0.4
        print(f"[END] success={str(success).lower()} steps={steps_taken} score={total_reward:.2f}", flush=True)
        return {"task": task_name, "score": total_reward, "success": success}

    except Exception as e:
        err = str(e).replace("\n", " ")
        print(f"[STEP] step={steps_taken+1} action=error reward=0.00 done=true error={err}", flush=True)
        print(f"[END] success=false steps={steps_taken} score=0.00", flush=True)
        return {"task": task_name, "score": 0.0, "success": False}


def main():
    results = []
    for difficulty in ["easy", "medium", "hard"]:
        result = run_task(difficulty)
        results.append(result)
    avg = sum(r["score"] for r in results) / len(results)
    print(f"\n[SUMMARY] tasks={len(results)} avg_score={avg:.2f}", flush=True)


if __name__ == "__main__":
    main()
