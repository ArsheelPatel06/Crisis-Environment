"""Task loading utilities for Crisis Intelligence Environment."""

import json
from pathlib import Path
from typing import Dict, Any, Optional


def load_task(difficulty: str) -> Dict[str, Any]:
    """
    Load a task dataset from JSON files.

    Args:
        difficulty: "easy", "medium", or "hard"

    Returns:
        Dictionary with keys:
        - input: raw task data with incidents
        - ground_truth: expected outputs (cleaned_data, priorities, allocation)
        - metadata: dataset info

    Raises:
        FileNotFoundError: if dataset file not found
        ValueError: if difficulty not recognized
    """
    difficulty = difficulty.lower().strip()
    if difficulty not in ["easy", "medium", "hard"]:
        raise ValueError(f"difficulty must be 'easy', 'medium', or 'hard', got '{difficulty}'")

    # Look for data file
    data_dir = Path(__file__).parent.parent / "data"
    task_file = data_dir / f"{difficulty}.json"

    if not task_file.exists():
        raise FileNotFoundError(f"Dataset not found: {task_file}")

    # Load and parse
    with open(task_file, "r") as f:
        task_data = json.load(f)

    print(f"✓ Loaded {difficulty} task: {task_file}")
    print(f"  Incidents: {len(task_data.get('input', {}).get('incidents', []))}")
    print(f"  Resource units: {task_data.get('input', {}).get('resource_units_total', 'N/A')}")

    return task_data


def list_available_tasks() -> list[str]:
    """List available task difficulties."""
    data_dir = Path(__file__).parent.parent / "data"
    available = []
    for diff in ["easy", "medium", "hard"]:
        if (data_dir / f"{diff}.json").exists():
            available.append(diff)
    return available


def get_task_metadata(task: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata about a task."""
    return {
        "schema_version": task.get("schema_version"),
        "dataset_id": task.get("dataset_id"),
        "num_incidents": len(task.get("input", {}).get("incidents", [])),
        "total_resources": task.get("input", {}).get("resource_units_total", 0),
        "num_ground_truth_items": {
            "cleaned_data": len(task.get("ground_truth", {}).get("cleaned_data", {})),
            "priorities": len(task.get("ground_truth", {}).get("priorities", {})),
            "allocation": len(task.get("ground_truth", {}).get("allocation", {})),
        }
    }
