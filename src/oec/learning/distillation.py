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
from oec.learning.errors import BackendNotAvailableError, LearningError
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
    details: dict[str, Any] = Field(default_factory=dict)


def _tabular_xy(dataset: LearningDataset) -> tuple[list[list[float]], list[float]] | None:
    xs: list[list[float]] = []
    ys: list[float] = []
    for row in dataset.records:
        raw_x = row.get("x", row.get("features"))
        raw_y = row.get("y", row.get("target"))
        if raw_x is None or raw_y is None:
            return None
        if isinstance(raw_x, (int, float)):
            xs.append([float(raw_x)])
        elif isinstance(raw_x, (list, tuple)) and raw_x:
            xs.append([float(value) for value in raw_x])
        else:
            return None
        ys.append(float(raw_y))
    if len(xs) < 2:
        return None
    width = len(xs[0])
    if any(len(row) != width for row in xs):
        return None
    return xs, ys


def _float_metrics(payload: dict[str, Any]) -> dict[str, float]:
    return {
        key: float(value)
        for key, value in payload.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }


def distill(
    *,
    teacher: ModelRef,
    student: ModelRef,
    dataset: LearningDataset,
    config: DistillationConfig | None = None,
) -> DistillationResult:
    """Governed distill entry. Tabular records call ``neural.distill_mlp``."""
    dataset.verify_integrity()
    cfg = config or DistillationConfig()
    try:
        import torch  # noqa: F401
    except ImportError as exc:
        raise BackendNotAvailableError(
            "distillation requires oec[neural] / torch",
            details={"error_type": type(exc).__name__},
        ) from exc

    tabular = _tabular_xy(dataset)
    if tabular is None:
        raise LearningError(
            "distillation requires tabular x/y (or features/target) records; "
            "SFT text-only / FM distillation is not implemented",
            details={
                "path": "fm-text-unwired",
                "dataset_kind": str(dataset.kind),
                "dataset_name": dataset.name,
            },
        )

    from oec.kernel.neural.distillation import distill_mlp
    from oec.kernel.neural.training import train_mlp
    from oec.neural.contracts import (
        DatasetSpec,
        DistillationSpec,
        NeuralModelSpec,
        TrainingSpec,
    )

    features, targets = tabular
    spec = DatasetSpec(x=features, y=targets, val_fraction=0.0)
    input_dim = len(features[0])
    epochs = min(cfg.max_epochs, 20)
    batch_size = min(len(features), 8)
    teacher_model = NeuralModelSpec(input_dim=input_dim, hidden_dims=[8])
    student_model = NeuralModelSpec(input_dim=input_dim, hidden_dims=[4])
    teacher_out = train_mlp(
        spec,
        teacher_model,
        TrainingSpec(epochs=epochs, batch_size=batch_size, seed=cfg.seed),
    )
    # S2 scalar regression forbids temperature != 1.0 (dimensional targets).
    student_out = distill_mlp(
        spec,
        teacher_out.checkpoint,
        student_model,
        TrainingSpec(epochs=epochs, batch_size=batch_size, seed=cfg.seed + 1),
        DistillationSpec(temperature=1.0, soft_weight=cfg.alpha),
        teacher_normalize=teacher_out.normalize,
    )
    metrics: dict[str, float] = {}
    if student_out.history:
        metrics["loss"] = float(student_out.history[-1]["train_loss"])
    metrics.update(
        {f"train_{key}": value for key, value in _float_metrics(student_out.train_metrics).items()}
    )
    if student_out.val_metrics:
        metrics.update(
            {f"val_{key}": value for key, value in _float_metrics(student_out.val_metrics).items()}
        )
    return DistillationResult(
        teacher=teacher,
        student=student,
        status="ok",
        metrics=metrics,
        message=(
            "neural.distill_mlp executed "
            f"(requested_temperature={cfg.temperature}, alpha={cfg.alpha}, seed={cfg.seed})"
        ),
        details={
            "path": "neural.distill_mlp",
            "epochs_ran": student_out.epochs_ran,
            "regression_temperature": 1.0,
        },
    )


def compare_base_vs_distilled(
    base: TrainingResult | DistillationResult | dict[str, float],
    distilled: TrainingResult | DistillationResult | dict[str, float],
) -> dict[str, Any]:
    bench = Benchmark(
        name="base-vs-distilled",
        metrics=(MetricSpec(name="loss", direction=MetricDirection.MINIMIZE),),
    )
    base_metrics = (
        base.metrics if isinstance(base, (TrainingResult, DistillationResult)) else dict(base)
    )
    distilled_metrics = (
        distilled.metrics
        if isinstance(distilled, (TrainingResult, DistillationResult))
        else dict(distilled)
    )
    return compare_results(
        bench, base_metrics, distilled_metrics, left_id="base", right_id="distilled"
    )


# Satisfy protocol-shaped naming without importing HF.
DISTILL_METHOD = TrainingMethod.DISTILL
