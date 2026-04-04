"""
Crisis Intelligence Environment - OpenEnv Protocol Implementation

Single-step reinforcement learning environment for crisis resource allocation.
Agents predict cleaned_data, priorities, and resource allocation in one step.
After prediction, episode is complete (done=True).
"""

import uuid
import json
import copy
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

from env.tasks import load_task
from env.grader import final_score, component_scores


def normalize_incident(incident):
    """Normalize incident - only convert numeric values, preserve text for parsing."""
    if not isinstance(incident, dict):
        raise ValueError(f"Invalid incident: expected dict, got {type(incident).__name__}")

    if "incident_id" not in incident:
        raise ValueError("Invalid incident: missing required field 'incident_id'")

    normalized = incident.copy()

    # Only convert numeric severity to int, preserve text for agent parsing
    if "severity" in normalized and normalized["severity"] is not None:
        try:
            normalized["severity"] = int(normalized["severity"])
        except (ValueError, TypeError):
            # Keep as-is if not numeric (e.g., "HIGH", "III")
            normalized["severity"] = normalized["severity"]

    # Convert people_affected to int if possible
    if "people_affected" in normalized and normalized["people_affected"] is not None:
        try:
            # Handle string numbers like "1,100" or "60"
            if isinstance(normalized["people_affected"], str):
                normalized["people_affected"] = int(normalized["people_affected"].replace(",", "").replace("+", ""))
            else:
                normalized["people_affected"] = int(normalized["people_affected"])
        except (ValueError, TypeError):
            # Keep as-is if not convertible (agent will handle)
            normalized["people_affected"] = normalized["people_affected"]

    return normalized


class CrisisEnv:
    """
    OpenEnv-compatible environment for crisis resource allocation.

    Protocol:
    - reset(difficulty) → observation with input data
    - step(prediction) → (observation, reward, done, info) where done=True immediately
    - Single step per episode
    """

    def __init__(self):
        """Initialize environment (no configuration needed)."""
        self.episode_id: Optional[str] = None
        self.difficulty: Optional[str] = None
        self.task_data: Optional[Dict[str, Any]] = None
        self.ground_truth: Optional[Dict[str, Any]] = None
        self.step_count: int = 0
        self.done: bool = False
        print("✓ CrisisEnv initialized (ready to reset)")

    def reset(self, difficulty: str = "easy") -> Dict[str, Any]:
        """
        Reset environment with a new task.

        Args:
            difficulty: "easy", "medium", or "hard"

        Returns:
            observation: {
                "episode_id": str,
                "difficulty": str,
                "input": { raw contaminated data },
                "metadata": { task details }
            }

        Raises:
            ValueError: If difficulty is invalid or incident parsing fails
        """
        # Validate difficulty
        valid_difficulties = ["easy", "medium", "hard"]
        if difficulty.lower() not in valid_difficulties:
            raise ValueError(f"Invalid difficulty: {difficulty}. Must be one of {valid_difficulties}")

        # Generate episode ID
        self.episode_id = str(uuid.uuid4())
        self.difficulty = difficulty.lower()
        self.step_count = 0
        self.done = False

        # Load task
        print(f"\n{'='*70}")
        print(f"📋 RESET: Loading {self.difficulty} task")
        print(f"{'='*70}")

        try:
            self.task_data = load_task(self.difficulty)
        except Exception as e:
            raise ValueError(f"Failed to load task for difficulty '{self.difficulty}': {str(e)}")

        self.ground_truth = self.task_data.get("ground_truth", {})

        # Build observation with normalized incident data
        input_data = copy.deepcopy(self.task_data.get("input", {}))

        # Defensive parsing: normalize all incidents with error handling
        if "incidents" in input_data:
            try:
                input_data["incidents"] = [normalize_incident(inc) for inc in input_data["incidents"]]
            except Exception as e:
                raise ValueError(f"Invalid incident data: {str(e)}")

        # Validate resource_units_total
        try:
            if "resource_units_total" in input_data:
                input_data["resource_units_total"] = int(input_data["resource_units_total"])
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid resource_units_total: must be numeric. Got '{input_data.get('resource_units_total')}'")

        observation = {
            "episode_id": self.episode_id,
            "difficulty": self.difficulty,
            "input": input_data,
            "metadata": {
                "schema_version": self.task_data.get("schema_version"),
                "dataset_id": self.task_data.get("dataset_id"),
            }
        }

        print(f"✓ Episode reset")
        print(f"  Episode ID: {self.episode_id}")
        print(f"  Incidents to clean: {len(observation['input'].get('incidents', []))}")
        print(f"  Total resources: {observation['input'].get('resource_units_total')}")

        return observation

    def get_ground_truth(self) -> Dict[str, Any]:
        """Get the ground truth for current episode."""
        return self.ground_truth or {}

    def get_input(self) -> Dict[str, Any]:
        """Get the raw input data for current episode."""
        if self.task_data:
            return self.task_data.get("input", {})
        return {}

    def step(self, prediction: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        Execute one step: evaluate prediction against ground truth.

        After this step, episode is DONE (done=True).

        Args:
            prediction: {
                "cleaned_data": {...},
                "priorities": {...},
                "allocation": {...}
            }

        Returns:
            observation: Same structure as reset observation
            reward: float in [0, 1.0]
            done: bool (always True after one step)
            info: {
                "scores": {
                    "cleaning": float,
                    "priority": float,
                    "allocation": float,
                    "final": float,
                    "perfect_match": bool
                },
                "explanation": {
                    "cleaning_feedback": str,
                    "priority_feedback": str,
                    "allocation_feedback": str
                }
            }
        """
        self.step_count += 1
        self.done = True  # Single-step episodes

        print(f"\n{'='*70}")
        print(f"🎯 STEP: Evaluating prediction")
        print(f"{'='*70}")

        # Verify ground truth exists
        if not self.ground_truth:
            raise ValueError("No ground truth loaded. Call reset() first.")

        # Score the prediction
        reward, scores, perfect = final_score(prediction, self.ground_truth)

        # Get component scores for detailed feedback
        component = component_scores(prediction, self.ground_truth)

        # Print debug info
        gt_cleaned = self.ground_truth.get("cleaned_data", {})
        gt_priorities = self.ground_truth.get("priorities", {})
        gt_allocation = self.ground_truth.get("allocation", {})
        pred_cleaned = prediction.get("cleaned_data", {})
        pred_priorities = prediction.get("priorities", {})
        pred_allocation = prediction.get("allocation", {})

        print(f"\nGround Truth Structure:")
        print(f"  Cleaned data incidents: {list(gt_cleaned.keys())}")
        print(f"  Priorities: {list(gt_priorities.keys())}")
        print(f"  Allocations: {list(gt_allocation.keys())}")

        print(f"\nPrediction Structure:")
        print(f"  Cleaned data incidents: {list(pred_cleaned.keys())}")
        print(f"  Priorities: {list(pred_priorities.keys())}")
        print(f"  Allocations: {list(pred_allocation.keys())}")

        print(f"\n📊 Scoring Components:")
        print(f"  Cleaning:   {component['cleaning']:.4f} / 0.5000")
        print(f"  Priority:   {component['priority']:.4f} / 0.2000")
        print(f"  Allocation: {component['allocation']:.4f} / 0.3000")

        print(f"\n🏆 Final Reward: {reward:.4f} / 1.0000")
        print(f"✓ Step complete. Episode done: {self.done}")

        # Generate explanations
        explanations = self._generate_explanations(prediction, component)

        # Build info dict
        info = {
            "scores": {
                **component,
                "final": reward,
            },
            "explanation": explanations,
        }

        # Build observation with normalized incident data
        input_data = copy.deepcopy(self.task_data.get("input", {}))

        # Defensive parsing: normalize all incidents
        if "incidents" in input_data:
            try:
                input_data["incidents"] = [normalize_incident(inc) for inc in input_data["incidents"]]
            except Exception as e:
                print(f"⚠️  Warning: Failed to normalize incidents in step observation: {str(e)}")
                # Proceed with unnormalized data rather than fail
                pass

        # Validate resource_units_total
        try:
            if "resource_units_total" in input_data:
                input_data["resource_units_total"] = int(input_data["resource_units_total"])
        except (ValueError, TypeError):
            print(f"⚠️  Warning: Invalid resource_units_total, keeping as-is")
            pass

        observation = {
            "episode_id": self.episode_id,
            "difficulty": self.difficulty,
            "input": input_data,
            "metadata": {
                "schema_version": self.task_data.get("schema_version"),
                "dataset_id": self.task_data.get("dataset_id"),
            }
        }

        return observation, reward, self.done, info

    def _generate_explanations(self, prediction: Dict[str, Any], component: Dict[str, float]) -> Dict[str, str]:
        """
        Generate rule-based explanations for each component.

        Returns dict with keys: cleaning_feedback, priority_feedback, allocation_feedback
        """
        explanations = {}

        # Cleaning feedback
        cleaning_score = component.get("cleaning", 0.0)
        if cleaning_score >= 0.50:
            explanations["cleaning_feedback"] = f"✓ Cleaning perfect ({cleaning_score:.3f}): All incidents correctly parsed, types matched, no formatting issues."
        elif cleaning_score >= 0.40:
            explanations["cleaning_feedback"] = f"◑ Cleaning very good ({cleaning_score:.3f}): Most incidents correct, minor type mismatches or formatting."
        elif cleaning_score >= 0.20:
            explanations["cleaning_feedback"] = f"◐ Cleaning moderate ({cleaning_score:.3f}): ~50% accuracy, significant data parsing issues."
        else:
            explanations["cleaning_feedback"] = f"✗ Cleaning poor ({cleaning_score:.3f}): Major parsing failures, incorrect types, or missing incidents."

        # Priority feedback
        priority_score = component.get("priority", 0.0)
        pred_priorities = prediction.get("priorities", {})
        gt_priorities = self.ground_truth.get("priorities", {})
        priority_correct = sum(1 for iid, p in gt_priorities.items() if pred_priorities.get(iid) == p)

        if priority_score >= 0.20:
            explanations["priority_feedback"] = f"✓ Priority perfect ({priority_score:.3f}): {priority_correct}/{len(gt_priorities)} correct."
        elif priority_score >= 0.15:
            explanations["priority_feedback"] = f"◑ Priority good ({priority_score:.3f}): {priority_correct}/{len(gt_priorities)} correct, balanced across categories."
        elif priority_score >= 0.08:
            explanations["priority_feedback"] = f"◐ Priority moderate ({priority_score:.3f}): {priority_correct}/{len(gt_priorities)} correct, some misclassification."
        else:
            explanations["priority_feedback"] = f"✗ Priority poor ({priority_score:.3f}): {priority_correct}/{len(gt_priorities)} correct, significant category errors."

        # Allocation feedback
        allocation_score = component.get("allocation", 0.0)
        pred_allocation = prediction.get("allocation", {})
        gt_allocation = self.ground_truth.get("allocation", {})
        allocation_correct = sum(1 for iid, amt in gt_allocation.items() if int(pred_allocation.get(iid, 0)) == int(amt))

        if allocation_score >= 0.30:
            explanations["allocation_feedback"] = f"✓ Allocation perfect ({allocation_score:.3f}): Budget matched, {allocation_correct}/{len(gt_allocation)} exact."
        elif allocation_score >= 0.20:
            explanations["allocation_feedback"] = f"◑ Allocation good ({allocation_score:.3f}): {allocation_correct}/{len(gt_allocation)} exact, minor deviations acceptable."
        elif allocation_score >= 0.10:
            explanations["allocation_feedback"] = f"◐ Allocation moderate ({allocation_score:.3f}): Budget roughly met, {allocation_correct}/{len(gt_allocation)} precise."
        else:
            explanations["allocation_feedback"] = f"✗ Allocation poor ({allocation_score:.3f}): Major deviations, budget constraint violated."

        return explanations
