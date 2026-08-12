"""W4 — Neural experiment builders (sugar over ExperimentSpec + neural.* skills).

Does not execute training. Builds declarative multi-step plans that
``run_experiment`` / ``Engine.run_experiment`` can execute when
``oec[neural]`` is installed.

No arbitrary ``nn.Module`` / agent Python (ADR 0031).
"""

from __future__ import annotations

from typing import Any, Literal

from oec.experiment.specs import (
    ArtifactSpec,
    ExperimentSpec,
    ExperimentStep,
    MetricDirection,
    MetricSpec,
    ModelKind,
    ModelSpec,
    ValidationSpec,
)
from oec.experiment.specs import DatasetSpec as ExperimentDatasetSpec
from oec.experiment.specs import (
    TrainingSpec as ExperimentTrainingSpec,
)
from oec.neural.contracts import (
    DatasetSpec as NeuralDatasetSpec,
)
from oec.neural.contracts import (
    NeuralModelSpec,
)
from oec.neural.contracts import (
    TrainingSpec as NeuralTrainingSpec,
)

NeuralSkillId = Literal[
    "neural.mlp.regressor",
    "neural.mlp.classifier",
    "neural.training.supervised",
    "neural.training.gradient",
    "neural.training.hybrid",
    "neural.training.neuroevolution",
]


def neural_dataset_to_inputs(dataset: NeuralDatasetSpec) -> dict[str, Any]:
    """Map neural DatasetSpec arrays into skill-input fields."""
    return {
        "x": [list(row) for row in dataset.x],
        "y": list(dataset.y),
        "val_fraction": float(dataset.val_fraction),
    }


def mlp_regressor_inputs(
    *,
    dataset: NeuralDatasetSpec,
    model: NeuralModelSpec | None = None,
    training: NeuralTrainingSpec | None = None,
    hidden_dims: list[int] | None = None,
    epochs: int | None = None,
    lr: float | None = None,
    seed: int | None = None,
    device: str = "cpu",
    capacity: str | None = None,
    lr_scheduler: str = "none",
) -> dict[str, Any]:
    """Build ``neural.mlp.regressor`` inputs from contracts + overrides."""
    model = model or NeuralModelSpec(input_dim=len(dataset.x[0]), output_dim=1)
    training = training or NeuralTrainingSpec()
    inputs: dict[str, Any] = {
        **neural_dataset_to_inputs(dataset),
        "activation": model.activation.value
        if hasattr(model.activation, "value")
        else str(model.activation),
        "dropout": float(model.dropout),
        "epochs": int(epochs if epochs is not None else training.epochs),
        "batch_size": int(training.batch_size),
        "lr": float(lr if lr is not None else training.optimizer.lr),
        "early_stopping_patience": training.early_stopping_patience,
        "seed": int(seed if seed is not None else training.seed),
        "device": device,
        "normalize_x": bool(training.normalize_x),
        "lr_scheduler": lr_scheduler,
    }
    dims = hidden_dims if hidden_dims is not None else list(model.hidden_dims)
    if dims:
        inputs["hidden_dims"] = dims
    if capacity is not None:
        inputs["capacity"] = capacity
    return inputs


def build_mlp_regressor_experiment(
    *,
    dataset: NeuralDatasetSpec | dict[str, Any],
    experiment_id: str = "neural.mlp.regressor",
    model: NeuralModelSpec | None = None,
    training: NeuralTrainingSpec | None = None,
    seed: int = 42,
    epochs: int | None = None,
    hidden_dims: list[int] | None = None,
    lr: float | None = None,
    device: str = "cpu",
    capacity: str | None = None,
    lr_scheduler: str = "none",
    require_r2_min: float | None = None,
    title: str | None = None,
) -> ExperimentSpec:
    """Single-step MLP regressor experiment with optional R² gate."""
    if isinstance(dataset, dict):
        dataset = NeuralDatasetSpec.model_validate(dataset)
    training = training or NeuralTrainingSpec(seed=seed)
    inputs = mlp_regressor_inputs(
        dataset=dataset,
        model=model,
        training=training,
        hidden_dims=hidden_dims,
        epochs=epochs,
        lr=lr,
        seed=seed,
        device=device,
        capacity=capacity,
        lr_scheduler=lr_scheduler,
    )
    metrics = (
        MetricSpec(
            name="train_r2",
            path="result.train_metrics.r_squared",
            step_id="train",
            direction=MetricDirection.MAXIMIZE,
        ),
    )
    validation = ValidationSpec()
    if require_r2_min is not None:
        validation = ValidationSpec(metric_min={"train_r2": float(require_r2_min)})

    return ExperimentSpec(
        id=experiment_id,
        title=title or "MLP regressor training (W4)",
        seed=seed,
        required_extras=("neural",),
        dataset=ExperimentDatasetSpec(
            x=[list(r) for r in dataset.x],
            y=list(dataset.y),
            val_fraction=float(dataset.val_fraction),
        ),
        model=ModelSpec(
            kind=ModelKind.NEURAL,
            name="mlp",
            params={
                "hidden_dims": inputs.get("hidden_dims"),
                "activation": inputs.get("activation"),
            },
        ),
        training=ExperimentTrainingSpec(
            seed=seed,
            max_epochs=int(inputs["epochs"]),
            options={"lr": inputs["lr"], "lr_scheduler": lr_scheduler},
        ),
        metrics=metrics,
        validation=validation,
        artifacts=(ArtifactSpec(name="checkpoint", kind="checkpoint", required=False),),
        steps=(
            ExperimentStep(
                step_id="train",
                skill_id="neural.mlp.regressor",
                inputs=inputs,
            ),
        ),
    )


def build_neural_training_mode_experiment(
    *,
    mode: Literal["supervised", "gradient", "hybrid", "neuroevolution"],
    dataset: NeuralDatasetSpec | dict[str, Any],
    experiment_id: str | None = None,
    seed: int = 0,
    epochs: int = 20,
    max_evaluations: int = 6,
    inner_epochs: int = 10,
    title: str | None = None,
) -> ExperimentSpec:
    """ADR 0033 training modes as single-step experiments."""
    if isinstance(dataset, dict):
        dataset = NeuralDatasetSpec.model_validate(dataset)
    skill_map = {
        "supervised": "neural.training.supervised",
        "gradient": "neural.training.gradient",
        "hybrid": "neural.training.hybrid",
        "neuroevolution": "neural.training.neuroevolution",
    }
    skill_id = skill_map[mode]
    exp_id = experiment_id or f"neural.training.{mode}"
    inputs: dict[str, Any] = {
        **neural_dataset_to_inputs(dataset),
        "seed": seed,
        "epochs": epochs,
        "max_evaluations": max_evaluations,
        "inner_epochs": inner_epochs,
    }
    # Drop val_fraction if skill schemas ignore it — still OK if additionalProperties false?
    # training skills may not accept val_fraction — strip to common fields
    for key in list(inputs.keys()):
        if key == "val_fraction":
            del inputs[key]
    return ExperimentSpec(
        id=exp_id,
        title=title or f"Neural training mode {mode} (W4/ADR 0033)",
        seed=seed,
        required_extras=("neural",) if mode != "hybrid" else ("neural", "evolutionary"),
        metrics=(
            MetricSpec(
                name="status_ok",
                path="result.seed",
                step_id="train",
                direction=MetricDirection.TARGET,
                target=float(seed),
                target_abs_tol=0.0,
            ),
        ),
        steps=(ExperimentStep(step_id="train", skill_id=skill_id, inputs=inputs),),
    )
