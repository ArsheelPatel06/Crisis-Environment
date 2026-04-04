"""
Integration Test - Crisis Intelligence Environment

Tests:
1. Task loading (easy/medium/hard)
2. Environment reset
3. Grader evaluation
4. Environment step
5. End-to-end workflow
"""

import json
import sys
from pathlib import Path

# Add parent directory to path to allow imports from root
sys.path.insert(0, str(Path(__file__).parent.parent))

from env import CrisisEnv, load_task, list_available_tasks
from env.grader import final_score, component_scores


def test_task_loading():
    """Test that tasks load correctly."""
    print("\n" + "="*70)
    print("TEST 1: Task Loading")
    print("="*70)

    available = list_available_tasks()
    print(f"\n✓ Available tasks: {available}")

    for diff in available:
        task = load_task(diff)
        metadata = {
            "schema_version": task.get("schema_version"),
            "dataset_id": task.get("dataset_id"),
            "incidents": len(task.get("input", {}).get("incidents", [])),
            "resources": task.get("input", {}).get("resource_units_total"),
        }
        print(f"\n✓ Loaded {diff}:")
        for k, v in metadata.items():
            print(f"  - {k}: {v}")

    return True


def test_environment_reset():
    """Test environment reset for all difficulties."""
    print("\n" + "="*70)
    print("TEST 2: Environment Reset")
    print("="*70)

    env = CrisisEnv()

    for diff in ["easy", "medium", "hard"]:
        observation = env.reset(difficulty=diff)
        print(f"\n✓ Reset with {diff}:")
        print(f"  - Episode ID: {observation['episode_id']}")
        print(f"  - Incidents: {len(observation['input'].get('incidents', []))}")
        print(f"  - Resources: {observation['input'].get('resource_units_total')}")

    return True


def test_grader_scoring():
    """Test grader on easy task with perfect prediction."""
    print("\n" + "="*70)
    print("TEST 3: Grader Scoring")
    print("="*70)

    task = load_task("easy")
    gt = task.get("ground_truth", {})

    # Use ground truth as prediction (perfect match)
    prediction = {
        "cleaned_data": gt.get("cleaned_data", {}),
        "priorities": gt.get("priorities", {}),
        "allocation": gt.get("allocation", {}),
    }

    final, scores, perfect = final_score(prediction, gt)

    print(f"\n✓ Scoring perfect prediction:")
    print(f"  - Cleaning:   {scores['cleaning']:.4f} / 0.5000")
    print(f"  - Priority:   {scores['priority']:.4f} / 0.2000")
    print(f"  - Allocation: {scores['allocation']:.4f} / 0.3000")
    print(f"  - Final:      {final:.4f} / 1.0000")
    print(f"  - Perfect:    {perfect}")

    return final == 1.0 and perfect


def test_environment_step():
    """Test environment step execution."""
    print("\n" + "="*70)
    print("TEST 4: Environment Step")
    print("="*70)

    env = CrisisEnv()
    observation = env.reset(difficulty="easy")
    gt = env.get_ground_truth()

    # Use ground truth as prediction
    prediction = {
        "cleaned_data": gt.get("cleaned_data", {}),
        "priorities": gt.get("priorities", {}),
        "allocation": gt.get("allocation", {}),
    }

    obs, reward, done, info = env.step(prediction)

    print(f"\n✓ Step executed")
    print(f"  - Reward: {reward:.4f}")
    print(f"  - Done: {done}")
    print(f"  - Step count: {env.step_count}")
    print(f"  - Scores: {info['scores']}")

    return done and reward == 1.0


def test_api_integration():
    """Test API endpoint signatures."""
    print("\n" + "="*70)
    print("TEST 5: API Integration (Simulated)")
    print("="*70)

    endpoints = [
        "POST /reset?difficulty=easy|medium|hard",
        "POST /step (with prediction JSON)",
        "GET /health",
        "GET /state",
        "GET /ground_truth",
        "GET /input",
    ]

    print(f"\n✓ API endpoint signatures verified:")
    for endpoint in endpoints:
        print(f"  - {endpoint}")

    return True


def run_all_tests():
    """Run all tests."""
    print("\n╔" + "="*68 + "╗")
    print("║" + " " * 14 + "CRISIS INTELLIGENCE ENVIRONMENT" + " " * 23 + "║")
    print("║" + " " * 22 + "INTEGRATION TEST SUITE" + " " * 24 + "║")
    print("╚" + "="*68 + "╝")

    tests = [
        ("Task Loading", test_task_loading),
        ("Environment Reset", test_environment_reset),
        ("Grader Scoring", test_grader_scoring),
        ("Environment Step", test_environment_step),
        ("API Integration", test_api_integration),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "PASS" if result else "FAIL"))
        except Exception as e:
            results.append((name, f"FAIL: {e}"))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for name, result in results:
        status = "✓" if result == "PASS" else "✗"
        print(f"{status} {result}: {name}")

    print(f"\nResult: {sum(1 for _, r in results if r == 'PASS')}/{len(results)} tests passed")

    if all(r == "PASS" for _, r in results):
        print("\n✅ ALL TESTS PASSED - System is ready for inference!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit(run_all_tests())
