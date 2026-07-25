"""Unit tests for :class:`~oec.validation.numerical.NumericalDiagnosticsValidator`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from oec.common import VersionedRef
from oec.skills.loader.frontmatter import SkillFrontMatter
from oec.skills.loader.models import LoadedSkill
from oec.skills.schemas.manifest import (
    EntrypointSpec,
    SchemaRefs,
    SkillManifest,
    SkillStatus,
)
from oec.validation.base import Severity
from oec.validation.numerical import NumericalDiagnosticsValidator


def _make_skill() -> LoadedSkill:
    return LoadedSkill(
        manifest=SkillManifest(
            id="test.numerical_skill",
            version="0.1.0",
            status=SkillStatus.EXPERIMENTAL,
            domain="test",
            title="Numerical test skill",
            entrypoint=EntrypointSpec(module="implementation", function="execute"),
            schemas=SchemaRefs(input="input.schema.json", output="output.schema.json"),
            method=VersionedRef(id="test", version="1"),
        ),
        front_matter=SkillFrontMatter(
            id="test.numerical_skill",
            version="0.1.0",
            status=SkillStatus.EXPERIMENTAL,
            domain="test",
            title="Numerical test skill",
        ),
        path=Path("."),
        body="",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )


def _validate(diagnostics: dict[str, Any]) -> list:
    return NumericalDiagnosticsValidator().validate(_make_skill(), {}, {"value": 1.0}, diagnostics)


def test_empty_diagnostics_yields_no_outcomes() -> None:
    assert _validate({}) == []


def test_healthy_diagnostics_yield_no_warnings() -> None:
    outcomes = _validate(
        {
            "iterations": 10,
            "max_iterations": 100,
            "condition_number": 1e3,
            "residual": 1e-10,
            "tolerance": 1e-8,
        }
    )
    assert outcomes == []


def test_near_iteration_limit_warning() -> None:
    outcomes = _validate({"iterations": 90, "max_iterations": 100})
    assert len(outcomes) == 1
    assert outcomes[0].layer == "numerical"
    assert outcomes[0].severity == Severity.WARNING
    assert "near iteration limit" in outcomes[0].messages[0]


def test_exactly_at_90_percent_is_warning() -> None:
    outcomes = _validate({"iterations": 90, "max_iterations": 100})
    assert any("near iteration limit" in o.messages[0] for o in outcomes)


def test_below_90_percent_is_ok() -> None:
    outcomes = _validate({"iterations": 89, "max_iterations": 100})
    assert outcomes == []


def test_poorly_conditioned_warning() -> None:
    outcomes = _validate({"condition_number": 1e8 + 1})
    assert len(outcomes) == 1
    assert outcomes[0].severity == Severity.WARNING
    assert "poorly conditioned" in outcomes[0].messages[0]


def test_condition_number_at_threshold_is_ok() -> None:
    """Strictly greater than 1e8 triggers the warning."""
    outcomes = _validate({"condition_number": 1e8})
    assert outcomes == []


def test_residual_exceeds_tolerance_warning() -> None:
    """Out-of-tolerance residual is a warning, not an error (ADR 0007 / compute_status)."""
    outcomes = _validate({"residual": 1e-3, "tolerance": 1e-6})
    assert len(outcomes) == 1
    assert outcomes[0].severity == Severity.WARNING
    assert "residual exceeds tolerance" in outcomes[0].messages[0]


def test_residual_within_tolerance_ok() -> None:
    outcomes = _validate({"residual": 1e-9, "tolerance": 1e-6})
    assert outcomes == []


def test_negative_residual_uses_absolute_value() -> None:
    outcomes = _validate({"residual": -1e-3, "tolerance": 1e-6})
    assert len(outcomes) == 1
    assert outcomes[0].severity == Severity.WARNING


def test_multiple_warnings_are_all_reported() -> None:
    outcomes = _validate(
        {
            "iterations": 100,
            "max_iterations": 100,
            "condition_number": 1e12,
            "residual": 0.1,
            "tolerance": 1e-6,
        }
    )
    assert len(outcomes) == 3
    assert all(o.severity == Severity.WARNING for o in outcomes)
    messages = {o.messages[0] for o in outcomes}
    assert "near iteration limit" in messages
    assert "poorly conditioned" in messages
    assert "residual exceeds tolerance" in messages


def test_layer_class_attribute() -> None:
    assert NumericalDiagnosticsValidator.layer == "numerical"
