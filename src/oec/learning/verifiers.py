"""Deterministic bridge from OEC execution results to L11 rewards."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from oec.learning.environments import RewardSpec

_SUCCESS_STATUSES = frozenset({"ok", "success", "succeeded", "completed"})


def execution_result_scores(result: Mapping[str, Any]) -> dict[str, float]:
    """Return the complete deterministic verifier score vector for *result*."""
    status = str(result.get("status", "")).lower()
    return {
        "correct": 1.0 if status in _SUCCESS_STATUSES else 0.0,
        "units": 1.0 if result.get("units_ok") is True else 0.0,
        "constraints": 1.0 if result.get("constraint_ok") is True else 0.0,
        "tokens": 0.0,
        "latency": 0.0,
    }


def execution_result_reward(result: Mapping[str, Any], spec: RewardSpec) -> float:
    """Score an OEC ExecutionResult-like mapping with a closed RewardSpec."""
    return spec.reward(execution_result_scores(result))


to_verifier_scores = execution_result_scores
reward_from_execution_result = execution_result_reward
