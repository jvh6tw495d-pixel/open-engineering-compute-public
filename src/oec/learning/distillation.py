"""L6 — teacher → student distillation as a Learning workflow."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from oec.learning.contracts import (
    MetricDirection,
    MetricSpec,
    ModelRef,
    TrainingMethod,
    TrainingResult,
)
from oec.learning.datasets import LearningDataset
from oec.learning.errors import BackendNotAvailableError
from oec.learning.evaluation import Benchmark, compare_results


class DistillationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    temperature: float = Field(default=2.0, gt=0.0, le=20.0)
    alpha: float = Field(default=0.5, ge=0.0, le=1.0)
    seed: int = 0
    max_epochs: int = Field(default=2, ge=1, le=100)


class DistillationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    teacher: ModelRef
    student: ModelRef
    status: str
    metrics: dict[str, float] = Field(default_factory=dict)
    message: str = ""


def distill(
    *,
    teacher: ModelRef,
    student: ModelRef,
    dataset: LearningDataset,
    config: DistillationConfig | None = None,
) -> DistillationResult:
    """Governed distill entry. Uses neural.distill when torch is present."""
    _ = dataset
    cfg = config or DistillationConfig()
    try:
        import torch  # noqa: F401
    except ImportError as exc:
        raise BackendNotAvailableError(
            "distillation requires oec[neural] / torch",
            details={"error_type": type(exc).__name__},
        ) from exc
    # Torch is present: still return a contract result without inventing numbers.
    return DistillationResult(
        teacher=teacher,
        student=student,
        status="planned",
        metrics={},
        message=(
            "torch available; execute neural.distill skill for numbers "
            f"(temperature={cfg.temperature}, alpha={cfg.alpha}, seed={cfg.seed})"
        ),
    )


def compare_base_vs_distilled(
    base: TrainingResult | dict[str, float],
    distilled: TrainingResult | dict[str, float],
) -> dict[str, Any]:
    bench = Benchmark(
        name="base-vs-distilled",
        metrics=(MetricSpec(name="loss", direction=MetricDirection.MINIMIZE),),
    )
    return compare_results(bench, base, distilled, left_id="base", right_id="distilled")


# Satisfy protocol-shaped naming without importing HF.
DISTILL_METHOD = TrainingMethod.DISTILL
