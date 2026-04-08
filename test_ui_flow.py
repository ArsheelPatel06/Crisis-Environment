#!/usr/bin/env python3
"""Test the full UI flow without opening Gradio."""

import requests
import json

BASE_URL = "http://127.0.0.1:7860"

def test_flow():
    print("=" * 60)
    print("Testing Crisis Intelligence System Flow")
    print("=" * 60)

    # 1. Health Check
    print("\n1️⃣  Testing Health Check...")
    try:
        res = requests.get(f"{BASE_URL}/health", timeout=5)
        assert res.status_code == 200, f"Health check failed: {res.status_code}"
        data = res.json()
        print(f"   ✅ Health Status: {data.get('status')}")
        print(f"   ✅ Episode ID: {data.get('episode_id')}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False

    # 2. Reset Task
    print("\n2️⃣  Testing Reset (Easy)...")
    try:
        res = requests.post(f"{BASE_URL}/reset?difficulty=easy", timeout=10)
        assert res.status_code == 200, f"Reset failed: {res.status_code}"
        data = res.json()
        assert data.get("success"), "Reset returned success=false"
        observation = data.get("observation", {})
        episode_id = observation.get("episode_id")
        incidents = observation.get("input", {}).get("incidents", [])
        resource_total = observation.get("input", {}).get("resource_units_total", 0)
        print(f"   ✅ Episode ID: {episode_id}")
        print(f"   ✅ Incidents: {len(incidents)}")
        print(f"   ✅ Total Resources: {resource_total}")
        for inc in incidents:
            print(f"      - {inc.get('incident_id')}: severity={inc.get('severity')}, people={inc.get('people_affected')}")
    except Exception as e:
        print(f"   ❌ Reset failed: {e}")
        return False

    # 3. Step/Allocation
    print("\n3️⃣  Testing Step (Allocation)...")
    try:
        prediction = {
            "cleaned_data": {inc.get("incident_id"): {
                "severity": inc.get("severity"),
                "people_affected": inc.get("people_affected")
            } for inc in incidents if inc.get("incident_id")},
            "priorities": {inc.get("incident_id"): "medium" for inc in incidents if inc.get("incident_id")},
            "allocation": {inc.get("incident_id"): 20 for inc in incidents if inc.get("incident_id")},
        }

        res = requests.post(f"{BASE_URL}/step", json=prediction, timeout=10)
        assert res.status_code == 200, f"Step failed: {res.status_code}"
        data = res.json()
        assert data.get("success"), "Step returned success=false"
        reward = data.get("reward")
        scores = data.get("info", {}).get("scores", {})
        print(f"   ✅ Reward: {reward:.4f}")
        print(f"   ✅ Final Score: {scores.get('final', 0):.4f}")
        print(f"      - Cleaning: {scores.get('cleaning', 0):.4f}")
        print(f"      - Priority: {scores.get('priority', 0):.4f}")
        print(f"      - Allocation: {scores.get('allocation', 0):.4f}")
    except Exception as e:
        print(f"   ❌ Step failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_flow()
