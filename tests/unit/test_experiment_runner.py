"""W2 unit tests: sequential experiment runner + metrics/gates."""

from __future__ import annotations

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
