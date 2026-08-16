"""L11 — map OEC execution/validation outcomes to RewardSpec scores."""

from __future__ import annotations

from typing import Any

from oec.learning.environments import RewardSpec, VerifierScores, compute_reward

_OK_STATUSES = frozenset({"validated", "verified", "completed", "ok"})


def execution_result_scores(payload: dict[str, Any]) -> dict[str, float]:
    """Map an ExecutionResult-like dict to closed verifier scores. No LLM."""
    status = str(payload.get("status") or "").lower()
    correct = 1.0 if status in _OK_STATUSES else 0.0
    units_ok = payload.get("units_ok")
    units = (1.0 if correct else 0.0) if units_ok is None else (1.0 if units_ok else 0.0)
    constraints_ok = payload.get("constraints_ok", payload.get("constraint_ok", True))
    constraints = 1.0 if constraints_ok else 0.0
    tokens = float(payload.get("tokens") or 0.0)
    latency = float(payload.get("latency") or payload.get("duration_ms") or 0.0)
    return {
        "correct": correct,
        "units": units,
        "constraints": constraints,
        "tokens": tokens,
        "latency": latency,
    }


def execution_result_reward(payload: dict[str, Any], spec: RewardSpec | None = None) -> float:
    return compute_reward(execution_result_scores(payload), spec or RewardSpec())


def scores_from_execution(payload: dict[str, Any]) -> VerifierScores:
    scores = execution_result_scores(payload)
    return VerifierScores(**scores)


def reward_from_execution(payload: dict[str, Any], spec: RewardSpec | None = None) -> float:
    return execution_result_reward(payload, spec)
