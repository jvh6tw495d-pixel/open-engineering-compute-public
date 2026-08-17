"""Evaluation vs Benchmark (L4)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from oec.learning.contracts import MetricDirection, MetricSpec, TrainingResult
from oec.learning.errors import BenchmarkError


class EvaluationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    metrics: dict[str, float]
    notes: tuple[str, ...] = ()


class GoldenCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    expected: dict[str, float]
    abs_tol: float = 1e-6


class Benchmark(BaseModel):
    """Reproducible comparison protocol — not a single-run evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    name: str = Field(min_length=1)
    metrics: tuple[MetricSpec, ...] = Field(min_length=1)
    seeds: tuple[int, ...] = (0,)


def evaluate_metrics(values: dict[str, float]) -> EvaluationResult:
    return EvaluationResult(metrics=dict(values))


def compare_results(
    benchmark: Benchmark,
    left: TrainingResult | dict[str, float],
    right: TrainingResult | dict[str, float],
    *,
    left_id: str = "left",
    right_id: str = "right",
) -> dict[str, Any]:
    """Compare two runs under one frozen metric protocol."""
    left_m = left.metrics if isinstance(left, TrainingResult) else dict(left)
    right_m = right.metrics if isinstance(right, TrainingResult) else dict(right)
    rows: list[dict[str, Any]] = []
    for spec in benchmark.metrics:
        if spec.name not in left_m or spec.name not in right_m:
            raise BenchmarkError(
                f"metric {spec.name!r} missing from one run",
                details={"metric": spec.name, "left": left_id, "right": right_id},
            )
        lv = float(left_m[spec.name])
        rv = float(right_m[spec.name])
        if spec.direction is MetricDirection.MINIMIZE:
            winner = left_id if lv < rv else right_id if rv < lv else "tie"
        elif spec.direction is MetricDirection.MAXIMIZE:
            winner = left_id if lv > rv else right_id if rv > lv else "tie"
        else:
            target = 0.0 if spec.target is None else float(spec.target)
            left_err = abs(lv - target)
            right_err = abs(rv - target)
            if left_err < right_err:
                winner = left_id
            elif right_err < left_err:
                winner = right_id
            else:
                winner = "tie"
        rows.append(
            {
                "metric": spec.name,
                "direction": spec.direction.value,
                left_id: lv,
                right_id: rv,
                "winner": winner,
            }
        )
    return {
        "benchmark": benchmark.name,
        "left": left_id,
        "right": right_id,
        "comparisons": rows,
    }
