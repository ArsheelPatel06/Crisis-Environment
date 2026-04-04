#!/usr/bin/env python3
"""
API Test Script - Validates all endpoints with proper error handling
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:7860"

def test_health() -> bool:
    """Test health endpoint."""
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        data = r.json()
        print("✅ GET /health")
        print(f"   Status: {data['status']}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ GET /health: {e}")
        return False

def test_reset() -> Dict[str, Any] | None:
    """Test reset endpoint."""
    try:
        r = requests.post(f"{BASE_URL}/reset?difficulty=easy", timeout=10)
        data = r.json()
        print("✅ POST /reset?difficulty=easy")
        print(f"   Episode ID: {data['observation']['episode_id']}")
        print(f"   Incidents: {len(data['observation']['input'].get('incidents', []))}")
        print(f"   Resources: {data['observation']['input'].get('resource_units_total')}")
        return data
    except Exception as e:
        print(f"❌ POST /reset: {e}")
        return None

def test_ground_truth(reset_data: Dict[str, Any]) -> bool:
    """Test ground truth endpoint."""
    try:
        r = requests.get(f"{BASE_URL}/ground_truth", timeout=5)
        data = r.json()
        print("✅ GET /ground_truth")
        gt = data.get('ground_truth', {})
        print(f"   Cleaned data: {len(gt.get('cleaned_data', {}))} incidents")
        print(f"   Priorities: {len(gt.get('priorities', {}))} labels")
        print(f"   Allocation: {len(gt.get('allocation', {}))} allocations")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ GET /ground_truth: {e}")
        return False

def test_step(reset_data: Dict[str, Any]) -> bool:
    """Test step endpoint."""
    try:
        # Get ground truth
        r_gt = requests.get(f"{BASE_URL}/ground_truth", timeout=5)
        gt = r_gt.json().get('ground_truth', {})

        # Use ground truth as prediction (perfect match)
        prediction = {
            "cleaned_data": gt.get("cleaned_data", {}),
            "priorities": gt.get("priorities", {}),
            "allocation": gt.get("allocation", {}),
        }

        r = requests.post(f"{BASE_URL}/step", json=prediction, timeout=10)
        data = r.json()
        print("✅ POST /step")
        print(f"   Reward: {data['reward']:.4f}")
        print(f"   Done: {data['done']}")
        print(f"   Scores: cleaning={data['info']['scores']['cleaning']:.3f}, priority={data['info']['scores']['priority']:.3f}, allocation={data['info']['scores']['allocation']:.3f}")

        # Debug: print all keys in scores
        print(f"   DEBUG - All score keys: {list(data['info']['scores'].keys())}")

        print(f"   Final Score: {data['info']['scores']['final']:.3f}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ POST /step: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_state() -> bool:
    """Test state endpoint."""
    try:
        r = requests.get(f"{BASE_URL}/state", timeout=5)
        data = r.json()
        print("✅ GET /state")
        print(f"   Episode ID: {data['episode_id']}")
        print(f"   Step count: {data['step_count']}")
        print(f"   Done: {data['done']}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ GET /state: {e}")
        return False

def main():
    """Run all API tests."""
    print("\n" + "="*70)
    print("🧪 CRISIS INTELLIGENCE ENVIRONMENT - API TEST SUITE")
    print("="*70)
    print(f"\n   Target: {BASE_URL}")
    print("   (Make sure server is running: uvicorn server.app:app --port 7860)")

    # Test health first
    if not test_health():
        print("\n❌ Server is not running. Start it with:")
        print("   python -m uvicorn server.app:app --port 7860")
        return 1

    print()

    # Run sequence of tests
    reset_data = test_reset()
    if not reset_data:
        return 1

    print()

    tests = [
        ("ground_truth", lambda: test_ground_truth(reset_data)),
        ("step", lambda: test_step(reset_data)),
        ("state", test_state),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "PASS" if result else "FAIL"))
            print()
        except Exception as e:
            results.append((name, f"FAIL: {e}"))

    # Summary
    print("="*70)
    print("📊 TEST SUMMARY")
    print("="*70)

    all_tests = ["health", "reset"] + [name for name, _ in tests]
    for test_name in all_tests:
        # Find result
        if test_name == "health":
            print(f"✅ PASS - health")
        elif test_name == "reset":
            print(f"✅ PASS - reset")
        else:
            for name, result in results:
                if name == test_name:
                    status = "✅" if result == "PASS" else "❌"
                    print(f"{status} {result} - {name}")

    passes = sum(1 for _, r in results if r == "PASS") + 2  # +2 for health and reset
    total = len(results) + 2
    print(f"\nResult: {passes}/{total} tests passed")

    if passes == total:
        print("\n🎉 ALL TESTS PASSED - API is fully operational!")
        return 0
    else:
        print(f"\n❌ {total - passes} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
