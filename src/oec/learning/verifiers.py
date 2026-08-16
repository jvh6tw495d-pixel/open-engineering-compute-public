"""L11 — map OEC execution/validation outcomes to RewardSpec scores."""

from __future__ import annotations

import math
from typing import Any

from oec.learning.environments import RewardSpec, VerifierScores, compute_reward

_OK_STATUSES = frozenset({"validated", "verified", "completed", "ok"})


def _as_optional_bool(value: object, *, field: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field} must be a boolean if provided")


def _finite_nonneg(value: object, *, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(f"{field} must be a finite non-negative number")
    return number


def _efficiency_score(observed: float | None, budget: float | None) -> float:
    """Higher is better. Missing telemetry must not look like perfect efficiency."""
    if observed is None:
        return 0.0
    if not math.isfinite(observed) or observed < 0.0:
        raise ValueError("observed consumption must be a finite non-negative number")
    if observed == 0.0:
        return 1.0
    if budget is None or budget <= 0.0 or not math.isfinite(budget):
        return 0.0
    return max(0.0, 1.0 - observed / budget)


def execution_result_scores(payload: dict[str, Any]) -> dict[str, float]:
    """Map an ExecutionResult-like dict to closed verifier scores. No LLM.

    Missing verifier flags score 0 (do not invent success). ``tokens`` and
    ``latency`` outputs are efficiency scores in ``[0, 1]``.
    """
    status = str(payload.get("status") or "").lower()
    correct = 1.0 if status in _OK_STATUSES else 0.0
    units_flag = _as_optional_bool(payload.get("units_ok"), field="units_ok")
    units = 0.0 if units_flag is None else (1.0 if units_flag else 0.0)
    if "constraints_ok" in payload:
        constraints_flag = _as_optional_bool(payload.get("constraints_ok"), field="constraints_ok")
    elif "constraint_ok" in payload:
        constraints_flag = _as_optional_bool(payload.get("constraint_ok"), field="constraint_ok")
    else:
        constraints_flag = None
    constraints = 0.0 if constraints_flag is None else (1.0 if constraints_flag else 0.0)
    tokens_raw = payload.get("tokens")
    if "latency" in payload:
        latency_raw = payload.get("latency")
    elif "duration_ms" in payload:
        latency_raw = payload.get("duration_ms")
    else:
        latency_raw = None
    token_budget = payload.get("token_budget")
    latency_budget = payload.get("latency_budget", payload.get("duration_budget"))
    return {
        "correct": correct,
        "units": units,
        "constraints": constraints,
        "tokens": _efficiency_score(
            None if tokens_raw is None else _finite_nonneg(tokens_raw, field="tokens"),
            None if token_budget is None else _finite_nonneg(token_budget, field="token_budget"),
        ),
        "latency": _efficiency_score(
            None if latency_raw is None else _finite_nonneg(latency_raw, field="latency"),
            (
                None
                if latency_budget is None
                else _finite_nonneg(latency_budget, field="latency_budget")
            ),
        ),
    }


def execution_result_reward(payload: dict[str, Any], spec: RewardSpec | None = None) -> float:
    return compute_reward(execution_result_scores(payload), spec or RewardSpec())


def scores_from_execution(payload: dict[str, Any]) -> VerifierScores:
    scores = execution_result_scores(payload)
    return VerifierScores(**scores)


def reward_from_execution(payload: dict[str, Any], spec: RewardSpec | None = None) -> float:
    return execution_result_reward(payload, spec)
