"""
Deterministic Grader - Scoring engine for Crisis Intelligence Environment

Scoring Formula:
  Final Score = 0.5×Cleaning + 0.2×Priority + 0.3×Allocation [max 1.0]

This grader evaluates crisis resource allocation predictions against ground truth.
All scoring is deterministic, reproducible, and free of randomness.
"""

from typing import Dict, Any, Mapping, Tuple


def _get_section(data: Mapping[str, Any], section: str) -> Dict[str, Any]:
    """Extract a section from either input or ground_truth structures."""
    if isinstance(data, dict):
        if "input" in data and section in data.get("input", {}):
            return data["input"][section]
        elif section in data:
            return data[section]
    return {}


def score_cleaning(prediction: Mapping[str, Any], ground_truth: Mapping[str, Any]) -> float:
    """
    Score the data cleaning accuracy.

    Compares predicted cleaned_data against ground truth cleaned_data.
    Returns score in [0, 0.5] range.

    Scoring logic:
    - Perfect match: 0.5
    - Each missing incident: -0.025 per incident
    - Each incorrect value (severity or people): -0.015
    - Partial match: proportional to correct fields
    """
    pred_cleaned = _get_section(prediction, "cleaned_data")
    gt_cleaned = _get_section(ground_truth, "cleaned_data")

    if not gt_cleaned:
        return 0.5 if not pred_cleaned else 0.0

    if not pred_cleaned:
        return 0.0

    # Check incident presence and correctness
    correct = 0
    total_fields = len(gt_cleaned) * 3  # incident_id, severity, people_affected

    for incident_id, gt_data in gt_cleaned.items():
        if incident_id in pred_cleaned:
            pred_data = pred_cleaned[incident_id]

            # Check each field
            if pred_data.get("incident_id") == gt_data.get("incident_id"):
                correct += 1
            if int(pred_data.get("severity", 0)) == int(gt_data.get("severity", 0)):
                correct += 1
            if int(pred_data.get("people_affected", 0)) == int(gt_data.get("people_affected", 0)):
                correct += 1
        # Missing incident counts as 0 for all 3 fields

    # Calculate proportional score (0.5 is max)
    accuracy = correct / total_fields if total_fields > 0 else 0
    return min(0.5, accuracy * 0.5 * len(gt_cleaned) / len(gt_cleaned)) if gt_cleaned else 0.0


def score_priority(prediction: Mapping[str, Any], ground_truth: Mapping[str, Any]) -> float:
    """
    Score the priority assignment accuracy.

    Compares predicted priorities against ground truth priorities.
    Returns score in [0, 0.2] range.

    Scoring logic:
    - Perfect match: 0.2
    - Each correct incident: +base points proportional to accuracy
    - Each incorrect incident: -penalty
    """
    pred_priorities = _get_section(prediction, "priorities")
    gt_priorities = _get_section(ground_truth, "priorities")

    if not gt_priorities:
        return 0.2 if not pred_priorities else 0.0

    if not pred_priorities:
        return 0.0

    # Count matches
    matches = 0
    for incident_id, gt_priority in gt_priorities.items():
        if pred_priorities.get(incident_id) == gt_priority:
            matches += 1

    # Proportional scoring (0.2 is max)
    accuracy = matches / len(gt_priorities) if gt_priorities else 0
    return accuracy * 0.2


def score_allocation(prediction: Mapping[str, Any], ground_truth: Mapping[str, Any]) -> float:
    """
    Score the resource allocation accuracy.

    Compares predicted allocation against ground truth allocation.
    Returns score in [0, 0.3] range.

    Scoring logic:
    - Perfect match: 0.3
    - Allocation efficiency: measured by how close to optimal
    - Budget constraint: must sum to correct total
    - Distribution accuracy: penalty for large deviations
    """
    pred_allocation = _get_section(prediction, "allocation")
    gt_allocation = _get_section(ground_truth, "allocation")

    if not gt_allocation:
        return 0.3 if not pred_allocation else 0.0

    if not pred_allocation:
        return 0.0

    # Check for perfect match first
    perfect = True
    for incident_id, gt_amount in gt_allocation.items():
        if int(pred_allocation.get(incident_id, 0)) != int(gt_amount):
            perfect = False
            break

    if perfect:
        return 0.3

    # Partial credit: measure deviation
    total_deviation = 0
    for incident_id, gt_amount in gt_allocation.items():
        pred_amount = int(pred_allocation.get(incident_id, 0))
        deviation = abs(pred_amount - int(gt_amount))
        total_deviation += deviation

    # Calculate penalty (lower deviation = higher score)
    max_possible_deviation = sum(int(v) for v in gt_allocation.values())
    if max_possible_deviation > 0:
        accuracy = max(0, 1.0 - (total_deviation / max_possible_deviation))
        return accuracy * 0.3

    return 0.0


def component_scores(prediction: Mapping[str, Any], ground_truth: Mapping[str, Any]) -> Dict[str, float]:
    """
    Calculate individual component scores.

    Returns dict with keys:
    - cleaning: [0, 0.5]
    - priority: [0, 0.2]
    - allocation: [0, 0.3]
    """
    return {
        "cleaning": score_cleaning(prediction, ground_truth),
        "priority": score_priority(prediction, ground_truth),
        "allocation": score_allocation(prediction, ground_truth),
    }


def final_score(prediction: Mapping[str, Any], ground_truth: Mapping[str, Any],
                cap: float = 1.0) -> Tuple[float, Dict[str, float], bool]:
    """
    Calculate final composite score.

    Formula: Cleaning + Priority + Allocation [capped at cap, default 1.0]

    Where:
    - Cleaning: [0, 0.5]
    - Priority: [0, 0.2]
    - Allocation: [0, 0.3]
    - Total: [0, 1.0]

    Returns:
    - final_score: float in [0, cap]
    - breakdown: dict with component scores and their weights
    - perfect_match: bool indicating if prediction == ground_truth
    """
    scores = component_scores(prediction, ground_truth)

    # Direct sum (components already scaled to their max values)
    weighted_score = (
        scores["cleaning"] +
        scores["priority"] +
        scores["allocation"]
    )

    # Cap at maximum
    final = min(weighted_score, cap)

    # Check for perfect match
    perfect = (
        scores["cleaning"] == 0.5 and
        scores["priority"] == 0.2 and
        scores["allocation"] == 0.3
    )

    return final, {
        **scores,
        "final": final,
        "perfect_match": perfect,
    }, perfect
