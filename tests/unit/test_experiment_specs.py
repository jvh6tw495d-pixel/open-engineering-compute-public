"""W0: Scientific Spec Family JSON round-trip and validation (ADR 0035)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from oec.experiment import (
    SPEC_SCHEMA_VERSION,
    ArtifactSpec,
    DatasetSpec,
    ExperimentSpec,
    ExperimentStep,
    MetricSpec,
    ModelSpec,
    ProvenanceSpec,
    TrainingSpec,
    ValidationSpec,
)
from oec.experiment.specs import (
    ArtifactKind,
    DatasetKind,
    MetricDirection,
    ModelKind,
)


def test_schema_version_constant() -> None:
    assert SPEC_SCHEMA_VERSION == "0.1.0"


def test_experiment_spec_round_trip_json() -> None:
    spec = ExperimentSpec(
        id="demo.root_then_describe",
        title="Root + describe",
        seed=7,
        metrics=(
            MetricSpec(
                name="root",
                direction=MetricDirection.TARGET,
                path="result.root",
                step_id="solve",
                target=1.414213562,
            ),
        ),
        steps=(
            ExperimentStep(
                step_id="solve",
                skill_id="mathematics.solve_root",
                inputs={"expression": "x**2 - 2", "bracket": [0, 2]},
            ),
            ExperimentStep(
                step_id="describe",
                skill_id="statistics.describe",
                inputs={"values": [1.0, 2.0, 3.0]},
            ),
        ),
    )
    payload = spec.model_dump(mode="json")
    restored = ExperimentSpec.model_validate(payload)
    assert restored == spec
    assert restored.schema_version == "0.1.0"
    assert len(restored.steps) == 2
    assert restored.metrics[0].name == "root"


def test_experiment_spec_rejects_duplicate_step_ids() -> None:
    with pytest.raises(ValidationError, match="unique"):
        ExperimentSpec(
            id="bad",
            steps=(
                ExperimentStep(step_id="a", skill_id="mathematics.solve_root"),
                ExperimentStep(step_id="a", skill_id="statistics.describe"),
            ),
        )


def test_experiment_spec_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ExperimentSpec.model_validate({"id": "x", "not_a_field": 1})


def test_dataset_spec_tabular_and_path() -> None:
    tabular = DatasetSpec(
        kind=DatasetKind.TABULAR_ARRAYS,
        x=[[0.0], [1.0], [2.0]],
        y=[0.0, 1.0, 2.0],
        val_fraction=0.0,
    )
    assert tabular.model_dump(mode="json")["kind"] == "tabular_arrays"

    path_ds = DatasetSpec(kind=DatasetKind.PATH_REF, path="data/toy.json")
    assert path_ds.path == "data/toy.json"


def test_dataset_spec_rejects_ragged_x() -> None:
    with pytest.raises(ValidationError):
        DatasetSpec(x=[[1.0, 2.0], [3.0]], y=[0.0, 1.0])


def test_model_training_metric_artifact_provenance_round_trip() -> None:
    model = ModelSpec(kind=ModelKind.NEURAL, name="mlp", params={"hidden_dims": [16, 8]})
    training = TrainingSpec(seed=0, max_epochs=10, options={"lr": 1e-3})
    metric = MetricSpec(name="rmse", direction=MetricDirection.MINIMIZE, path="result.rmse")
    artifact = ArtifactSpec(
        name="ckpt",
        kind=ArtifactKind.CHECKPOINT,
        path="artifacts/model.pt",
        required=True,
    )
    provenance = ProvenanceSpec(capture_git_commit=False, extra_keys=("hostname",))
    validation = ValidationSpec(metric_max={"rmse": 0.5})

    for obj in (model, training, metric, artifact, provenance, validation):
        restored = type(obj).model_validate(obj.model_dump(mode="json"))
        assert restored == obj


def test_full_neural_oriented_experiment_shape() -> None:
    """Illustrative shape for future NeuralExperiment sugar (W4) — no runtime."""
    spec = ExperimentSpec(
        id="neural.mlp.toy",
        required_extras=("neural",),
        dataset=DatasetSpec(
            x=[[0.0], [1.0], [2.0], [3.0]],
            y=[1.0, 3.0, 5.0, 7.0],
        ),
        model=ModelSpec(
            kind=ModelKind.NEURAL,
            params={"architecture": "mlp", "hidden_dims": [8]},
        ),
        training=TrainingSpec(seed=42, max_epochs=20),
        metrics=(
            MetricSpec(name="val_loss", direction=MetricDirection.MINIMIZE, path="result.val_loss"),
        ),
        artifacts=(ArtifactSpec(name="checkpoint", kind=ArtifactKind.CHECKPOINT),),
        steps=(
            ExperimentStep(
                step_id="train",
                skill_id="neural.mlp.regressor",
                inputs={
                    "x": [[0.0], [1.0], [2.0], [3.0]],
                    "y": [1.0, 3.0, 5.0, 7.0],
                    "hidden_dims": [8],
                    "epochs": 20,
                    "seed": 42,
                    "device": "cpu",
                },
            ),
        ),
    )
    assert spec.required_extras == ("neural",)
    assert spec.steps[0].skill_id.startswith("neural.")
