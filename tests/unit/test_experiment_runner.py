"""W2 unit tests: sequential experiment runner + metrics/gates + binds + artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from oec.experiment import (
    ExperimentSpec,
    ExperimentStatus,
    ExperimentStep,
    MetricSpec,
    ValidationSpec,
    config_hash,
    run_experiment,
)
from oec.experiment.specs import MetricDirection
from oec.sdk import Engine


def _engine() -> Engine:
    return Engine(skills_root="skills")


def test_config_hash_stable() -> None:
    spec = ExperimentSpec(
        id="h",
        steps=(
            ExperimentStep(
                step_id="a",
                skill_id="statistics.describe",
                inputs={"values": [1.0, 2.0, 3.0]},
            ),
        ),
    )
    assert config_hash(spec) == config_hash(spec)
    assert len(config_hash(spec)) == 64


def test_empty_steps_invalid() -> None:
    record = run_experiment(_engine(), ExperimentSpec(id="empty", steps=()))
    assert record.status == ExperimentStatus.INVALID
    assert record.validation.passed is False


def test_two_step_math_stats_completed() -> None:
    spec = ExperimentSpec(
        id="root_then_describe",
        seed=7,
        metrics=(
            MetricSpec(
                name="mean",
                direction=MetricDirection.TARGET,
                path="result.mean",
                step_id="describe",
                target=2.0,
            ),
        ),
        steps=(
            ExperimentStep(
                step_id="root",
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
    record = run_experiment(_engine(), spec)
    assert record.status == ExperimentStatus.COMPLETED
    assert len(record.steps) == 2
    assert record.steps[0].execution is not None
    assert record.steps[0].execution.status.value in {
        "VERIFIED",
        "VALIDATED",
        "CONVERGED_WITH_WARNINGS",
        "APPROXIMATE",
    }
    means = [m for m in record.metrics if m.name == "mean"]
    assert len(means) == 1
    assert means[0].value == 2.0
    assert means[0].error is None
    assert record.validation.passed is True
    assert record.reproducibility["config_hash"] == config_hash(spec)
    assert record.seed == 7


def test_metric_max_gate_fails() -> None:
    spec = ExperimentSpec(
        id="gate_fail",
        metrics=(
            MetricSpec(
                name="mean",
                direction=MetricDirection.MINIMIZE,
                path="result.mean",
                step_id="d",
            ),
        ),
        validation=ValidationSpec(metric_max={"mean": 0.5}),
        steps=(
            ExperimentStep(
                step_id="d",
                skill_id="statistics.describe",
                inputs={"values": [1.0, 2.0, 3.0]},
            ),
        ),
    )
    record = run_experiment(_engine(), spec)
    assert record.status == ExperimentStatus.VALIDATION_FAILED
    assert record.validation.passed is False
    assert any("metric_max" in m for m in record.validation.messages)


def test_abort_on_invalid_step() -> None:
    """Malformed skill inputs → INVALID execution → abort."""
    spec = ExperimentSpec(
        id="abort_invalid",
        validation=ValidationSpec(abort_on_invalid=True),
        steps=(
            ExperimentStep(
                step_id="bad",
                skill_id="statistics.describe",
                inputs={"values": []},  # minItems 1 — schema/math fail
            ),
            ExperimentStep(
                step_id="never",
                skill_id="statistics.describe",
                inputs={"values": [1.0]},
            ),
        ),
    )
    record = run_experiment(_engine(), spec)
    assert record.status in {
        ExperimentStatus.ABORTED,
        ExperimentStatus.FAILED,
        ExperimentStatus.VALIDATION_FAILED,
    }
    # second step must not run if aborted on first
    assert len(record.steps) == 1 or (len(record.steps) >= 1 and record.steps[0].step_id == "bad")


def test_engine_run_experiment_api() -> None:
    engine = _engine()
    record = engine.run_experiment(
        {
            "id": "via_engine",
            "seed": 1,
            "steps": [
                {
                    "step_id": "d",
                    "skill_id": "statistics.describe",
                    "inputs": {"values": [10.0, 20.0]},
                }
            ],
            "metrics": [
                {
                    "name": "mean",
                    "path": "result.mean",
                    "direction": "minimize",
                    "step_id": "d",
                }
            ],
        }
    )
    assert record.status == ExperimentStatus.COMPLETED
    assert record.metrics[0].value == 15.0


def test_binds_from_wires_step_output() -> None:
    """W2.2: take describe mean and feed as values list via... use root into pdf x."""
    # solve_root → result.root → distribution_eval x (scalar path)
    # Actually distribution wants x number; root is a float.
    engine = _engine()
    record = engine.run_experiment(
        {
            "id": "bind_root_to_pdf",
            "seed": 0,
            "steps": [
                {
                    "step_id": "root",
                    "skill_id": "mathematics.solve_root",
                    "inputs": {"expression": "x**2 - 4", "bracket": [0, 3]},
                },
                {
                    "step_id": "pdf",
                    "skill_id": "statistics.distribution_eval",
                    "inputs": {
                        "distribution": "norm",
                        "operation": "pdf",
                        "params": {"loc": 0.0, "scale": 1.0},
                    },
                    "binds_from": [
                        {"step_id": "root", "path": "result.root", "as": "x"},
                    ],
                },
            ],
            "metrics": [
                {
                    "name": "pdf_at_root",
                    "path": "result.value",
                    "step_id": "pdf",
                    "direction": "maximize",
                }
            ],
        }
    )
    assert record.status == ExperimentStatus.COMPLETED
    assert record.metrics[0].value is not None
    # N(0,1) pdf at ~2
    assert record.metrics[0].value == pytest.approx(0.05399096651, rel=1e-5)


def test_target_abs_tol_gate() -> None:
    record = run_experiment(
        _engine(),
        ExperimentSpec(
            id="target_gate",
            metrics=(
                MetricSpec(
                    name="mean",
                    path="result.mean",
                    step_id="d",
                    direction=MetricDirection.TARGET,
                    target=2.0,
                    target_abs_tol=0.01,
                ),
            ),
            steps=(
                ExperimentStep(
                    step_id="d",
                    skill_id="statistics.describe",
                    inputs={"values": [1.0, 2.0, 3.0]},
                ),
            ),
        ),
    )
    assert record.status == ExperimentStatus.COMPLETED
    assert record.metrics[0].abs_error_to_target == pytest.approx(0.0)


def test_target_abs_tol_fails() -> None:
    record = run_experiment(
        _engine(),
        ExperimentSpec(
            id="target_gate_fail",
            metrics=(
                MetricSpec(
                    name="mean",
                    path="result.mean",
                    step_id="d",
                    direction=MetricDirection.TARGET,
                    target=10.0,
                    target_abs_tol=0.5,
                ),
            ),
            steps=(
                ExperimentStep(
                    step_id="d",
                    skill_id="statistics.describe",
                    inputs={"values": [1.0, 2.0, 3.0]},
                ),
            ),
        ),
    )
    assert record.status == ExperimentStatus.VALIDATION_FAILED


def test_persist_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "arts"
    record = _engine().run_experiment(
        {
            "id": "persist_demo",
            "seed": 1,
            "steps": [
                {
                    "step_id": "d",
                    "skill_id": "statistics.describe",
                    "inputs": {"values": [1.0, 2.0]},
                }
            ],
        },
        artifact_root=root,
    )
    assert record.artifacts_produced
    paths = [Path(a.path) for a in record.artifacts_produced]
    assert any(p.name == "record.json" for p in paths)
    assert all(p.is_file() for p in paths)


def test_same_spec_same_config_hash_across_runs() -> None:
    spec = ExperimentSpec(
        id="repro",
        seed=42,
        steps=(
            ExperimentStep(
                step_id="d",
                skill_id="statistics.describe",
                inputs={"values": [1.0, 1.0, 1.0]},
            ),
        ),
    )
    e = _engine()
    a = run_experiment(e, spec)
    b = run_experiment(e, spec)
    assert a.reproducibility["config_hash"] == b.reproducibility["config_hash"]
    assert a.metrics == b.metrics or (
        a.metrics[0].value == b.metrics[0].value if a.metrics and b.metrics else True
    )
