"""L11 — map OEC execution/validation outcomes to RewardSpec scores."""

from __future__ import annotations

from typing import Any

from oec.learning.environments import RewardSpec, VerifierScores, compute_reward

_OK_STATUSES = frozenset({"validated", "verified", "completed", "ok"})


def _efficiency_score(observed: float | None, budget: float | None) -> float:
    """Higher is better. Missing telemetry must not look like perfect efficiency."""
    if observed is None:
        return 0.0
    if observed < 0.0:
        raise ValueError("observed consumption must be non-negative")
    if observed == 0.0:
        return 1.0
    if budget is None or budget <= 0.0:
        return 0.0
    return max(0.0, 1.0 - observed / budget)


def execution_result_scores(payload: dict[str, Any]) -> dict[str, float]:
    """Map an ExecutionResult-like dict to closed verifier scores. No LLM.

    ``tokens`` and ``latency`` in the *output* are efficiency scores in
    ``[0, 1]`` (higher is better). Raw counts need ``token_budget`` /
    ``latency_budget`` to be converted; without a budget, any consumption
    scores 0 so it cannot inflate the reward.
    """
    status = str(payload.get("status") or "").lower()
    correct = 1.0 if status in _OK_STATUSES else 0.0
    units_ok = payload.get("units_ok")
    units = (1.0 if correct else 0.0) if units_ok is None else (1.0 if units_ok else 0.0)
    constraints_ok = payload.get("constraints_ok", payload.get("constraint_ok", True))
    constraints = 1.0 if constraints_ok else 0.0
    tokens_raw = payload.get("tokens")
    latency_raw = payload.get(
        "latency", payload.get("duration_ms") if "duration_ms" in payload else None
    )
    token_budget = payload.get("token_budget")
    latency_budget = payload.get("latency_budget", payload.get("duration_budget"))
    return {
        "correct": correct,
        "units": units,
        "constraints": constraints,
        "tokens": _efficiency_score(
            None if tokens_raw is None else float(tokens_raw),
            float(token_budget) if token_budget is not None else None,
        ),
        "latency": _efficiency_score(
            None if latency_raw is None else float(latency_raw),
            float(latency_budget) if latency_budget is not None else None,
        ),
    }


def execution_result_reward(payload: dict[str, Any], spec: RewardSpec | None = None) -> float:
    return compute_reward(execution_result_scores(payload), spec or RewardSpec())


def scores_from_execution(payload: dict[str, Any]) -> VerifierScores:
    scores = execution_result_scores(payload)
    return VerifierScores(**scores)


def reward_from_execution(payload: dict[str, Any], spec: RewardSpec | None = None) -> float:
    return execution_result_reward(payload, spec)
