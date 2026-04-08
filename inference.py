"""
Crisis Intelligence Environment - Inference Engine

Supports multiple agents: heuristic (default), random, greedy
Can be used as CLI or imported as library.

Library Usage:
  from inference import run_inference
  result = run_inference(difficulty="easy", agent="heuristic")

CLI Usage:
  python3 inference.py                 # Run heuristic agent (default)
  python3 inference.py --agent random  # Run random agent
  python3 inference.py --agent greedy  # Run greedy agent

Output format:
  [START] task=<task_name> env=<benchmark> model=<model_name>
  [STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END] success=<true|false> steps=<n> score=<0.00>
"""

import sys
import argparse
import requests
import json
import os
from agents.heuristic_agent import HeuristicCrisisAgent
from agents.random_agent import RandomCrisisAgent
from agents.greedy_agent import GreedyCrisisAgent
from agents.llm_agent import LLMCrisisAgent

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
BENCHMARK = "crisis-intelligence-env"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # For compliance, even if unused

# Agent mapping
AGENT_MAP = {
    "heuristic": (HeuristicCrisisAgent(), "heuristic-v1"),
    "random": (RandomCrisisAgent(), "random-baseline"),
    "greedy": (GreedyCrisisAgent(), "greedy-baseline"),
    "llm": (LLMCrisisAgent(), "llm-v1"),
}


def run_task(difficulty: str, agent_name: str = "heuristic"):
    """Run a single task and return results."""
    agent, MODEL_NAME = AGENT_MAP[agent_name]
    task_name = f"crisis-{difficulty}"

    # [START]
    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    try:
        # Reset environment
        res = requests.post(f"{BASE_URL}/reset?difficulty={difficulty}", timeout=10)
        res.raise_for_status()
        obs = res.json()["observation"]

        # Get prediction
        prediction = agent.generate_prediction(obs)

        # Execute step
        res = requests.post(f"{BASE_URL}/step", json=prediction, timeout=10)
        res.raise_for_status()
        result = res.json()

        reward = result["reward"]
        done = result["done"]
        success = done and reward > 0.5

        # [STEP]
        action_str = "allocate_resources"
        print(f"[STEP] step=1 action={action_str} reward={reward:.2f} done={str(done).lower()} error=null", flush=True)

        # [END]
        print(f"[END] success={str(success).lower()} steps=1 score={reward:.2f}", flush=True)

        return {
            "task": task_name,
            "difficulty": difficulty,
            "agent": agent_name,
            "reward": reward,
            "success": success,
            "scores": result["info"]["scores"]
        }

    except Exception as e:
        print(f"[STEP] step=1 action=error reward=0.00 done=true error={str(e)}", flush=True)
        print(f"[END] success=false steps=1 score=0.00", flush=True)
        return {
            "task": task_name,
            "difficulty": difficulty,
            "agent": agent_name,
            "reward": 0.0,
            "success": False,
            "error": str(e)
        }


def run_inference(difficulty: str = "easy", agent: str = "heuristic") -> dict:
    """
    Programmatic API for running inference.

    Args:
        difficulty: "easy", "medium", or "hard"
        agent: "heuristic", "random", or "greedy"

    Returns:
        dict with keys: task, difficulty, agent, reward, success, scores

    Example:
        result = run_inference("easy", "heuristic")
        print(f"Score: {result['reward']}")
    """
    if difficulty not in ["easy", "medium", "hard"]:
        raise ValueError(f"Invalid difficulty: {difficulty}")
    if agent not in AGENT_MAP:
        raise ValueError(f"Invalid agent: {agent}")

    return run_task(difficulty, agent)


def run_all(agent: str = "heuristic") -> dict:
    """
    Run all difficulties with specified agent.

    Args:
        agent: "heuristic", "random", or "greedy"

    Returns:
        dict with results for all difficulties
    """
    results = []
    for difficulty in ["easy", "medium", "hard"]:
        result = run_task(difficulty, agent)
        results.append(result)

    return {
        "agent": agent,
        "tasks": results,
        "average_score": sum(r["reward"] for r in results) / len(results) if results else 0.0,
        "total_reward": sum(r["reward"] for r in results),
    }


def main():
    """CLI entry point."""
    # Log Python version at startup
    print(f"[INFO] Python version: {sys.version}", flush=True)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run inference with different agents")
    parser.add_argument("--agent", choices=["heuristic", "random", "greedy", "llm"], default="heuristic", help="Agent to use (default: heuristic)")
    args = parser.parse_args()

    # Run all tasks with specified agent
    results = run_all(args.agent)

    return results


if __name__ == "__main__":
    main()
