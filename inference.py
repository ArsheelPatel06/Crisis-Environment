"""
Crisis Intelligence Environment - Baseline Inference Script
"""

import sys
import os
import json
import re
import requests
from openai import OpenAI

print(f"[INFO] Python version: {sys.version}", flush=True)

# -------------------- ENV --------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")
ENV_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

BENCHMARK = "crisis-intelligence-env"

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

# -------------------- SYSTEM PROMPT --------------------
SYSTEM_PROMPT = """You are a crisis resource allocation AI agent.
Return ONLY valid JSON with no explanation or markdown.

Phase 1 - clean corrupted data:
{"cleaned_data": {"INC-001": {"incident_id": "INC-001", "severity": 5, "people_affected": 800}}}

Phase 2 - assign priorities (high/medium/low):
{"priorities": {"INC-001": "high", "INC-002": "medium", "INC-003": "low"}}

Phase 3 - allocate integer resources summing to total:
{"allocation": {"INC-001": 25, "INC-002": 15, "INC-003": 10}}

Rules:
- severity = integer 1-5
- people_affected = integer
- priorities = high / medium / low
- allocation = integers
"""

# -------------------- LLM CALL --------------------
def call_llm(user_msg: str) -> dict:
    try:
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

        # Clean markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        # Extract JSON
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

        return json.loads(text)

    except Exception as e:
        print("[LLM ERROR]:", str(e))
        return {}

# -------------------- MAIN TASK --------------------
def run_task(difficulty: str) -> dict:
    task_name = f"crisis-{difficulty}"
    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    total_reward = 0.0
    steps_taken = 0

    try:
        # RESET ENV
        res = requests.post(f"{ENV_URL}/reset", params={"difficulty": difficulty}, timeout=15)
        res.raise_for_status()

        obs = res.json()["observation"]
        input_data = obs["input"]

        incidents = input_data.get("incidents", [])
        resource_total = input_data.get("resource_units_total", 50)

        # -------------------- PHASE 1 --------------------
        steps_taken += 1

        msg1 = f"Phase 1: Clean data. Incidents: {json.dumps(incidents)}"
        action1 = call_llm(msg1)

        if not action1 or "cleaned_data" not in action1:
            print("[FALLBACK] clean_data")
            cleaned = {}
            for inc in incidents:
                iid = inc.get("incident_id", "UNK")
                cleaned[iid] = {
                    "incident_id": iid,
                    "severity": 3,
                    "people_affected": 100
                }
            action1 = {"cleaned_data": cleaned}

        res = requests.post(f"{ENV_URL}/step", json=action1, timeout=15)
        res.raise_for_status()

        r = res.json()
        r1, done = r["reward"], r["done"]
        total_reward += r1
        obs = r["observation"]

        print(f"[STEP] step={steps_taken} action=clean_data reward={r1:.2f} done={str(done).lower()} error=null", flush=True)

        # -------------------- PHASE 2 --------------------
        steps_taken += 1

        msg2 = f"Phase 2: Assign priorities. Incidents: {json.dumps(incidents)}"
        action2 = call_llm(msg2)

        if not action2 or "priorities" not in action2:
            print("[FALLBACK] priorities")
            priorities = {}
            for inc in incidents:
                iid = inc.get("incident_id", "UNK")
                priorities[iid] = "medium"
            action2 = {"priorities": priorities}

        res = requests.post(f"{ENV_URL}/step", json=action2, timeout=15)
        res.raise_for_status()

        r = res.json()
        r2, done = r["reward"], r["done"]
        total_reward += r2
        obs = r["observation"]

        print(f"[STEP] step={steps_taken} action=assign_priorities reward={r2:.2f} done={str(done).lower()} error=null", flush=True)

        # -------------------- PHASE 3 --------------------
        steps_taken += 1

        msg3 = f"Phase 3: Allocate {resource_total} units. Incidents: {json.dumps(incidents)}"
        action3 = call_llm(msg3)

        if not action3 or "allocation" not in action3:
            print("[FALLBACK] allocation")

            allocation = {}
            num = max(1, len(incidents))
            per = max(1, resource_total // num)

            for inc in incidents:
                iid = inc.get("incident_id", "UNK")
                allocation[iid] = per

            action3 = {"allocation": allocation}

        res = requests.post(f"{ENV_URL}/step", json=action3, timeout=15)
        res.raise_for_status()

        r = res.json()
        r3, done = r["reward"], r["done"]
        total_reward += r3

        print(f"[STEP] step={steps_taken} action=allocate_resources reward={r3:.2f} done={str(done).lower()} error=null", flush=True)

        # -------------------- END --------------------
        success = done and total_reward > 0.4

        print(f"[END] success={str(success).lower()} steps={steps_taken} score={total_reward:.2f}", flush=True)

        return {
            "task": task_name,
            "score": total_reward,
            "success": success
        }

    except Exception as e:
        err = str(e).replace("\n", " ")
        print(f"[STEP] step={steps_taken+1} action=error reward=0.00 done=true error={err}", flush=True)
        print(f"[END] success=false steps={steps_taken} score=0.00", flush=True)

        return {
            "task": task_name,
            "score": 0.0,
            "success": False
        }

# -------------------- MAIN --------------------
def main():
    results = []

    for difficulty in ["easy", "medium", "hard"]:
        result = run_task(difficulty)
        results.append(result)

    avg = sum(r["score"] for r in results) / len(results)
    print(f"\n[SUMMARY] tasks={len(results)} avg_score={avg:.2f}", flush=True)


if __name__ == "__main__":
    main()