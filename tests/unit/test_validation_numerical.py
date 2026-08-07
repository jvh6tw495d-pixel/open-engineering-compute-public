"""Unit tests for :class:`~oec.validation.numerical.NumericalDiagnosticsValidator`.

``max_iterations``/``tolerance`` are read from ``normalized_inputs``
(the caller's own request), not ``diagnostics`` -- no shipped skill
echoes either one back into its diagnostics dict. This was a real bug
(ADR 0014, Finding 2 of the Sprint 05 independent review): the original
Sprint 03 shape read both from ``diagnostics`` alone, so these checks
could never fire for any real skill.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from oec.skills.loader.frontmatter import SkillFrontMatter
from oec.skills.loader.models import LoadedSkill
from oec.skills.schemas.manifest import (
    EntrypointSpec,
    MethodRef,
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
            method=MethodRef(id="test", version="1", iterative=False),
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


def _validate(diagnostics: dict[str, Any], normalized_inputs: dict[str, Any] | None = None) -> list:
    return NumericalDiagnosticsValidator().validate(
        _make_skill(), normalized_inputs or {}, {"value": 1.0}, diagnostics
    )


def test_empty_diagnostics_yields_no_outcomes() -> None:
    assert _validate({}) == []


def test_healthy_diagnostics_yield_no_warnings() -> None:
    outcomes = _validate(
        {"iterations": 10, "condition_number": 1e3, "residual": 1e-10},
        {"max_iterations": 100, "tolerance": 1e-8},
    )
    assert outcomes == []


def test_near_iteration_limit_warning() -> None:
    outcomes = _validate({"iterations": 90}, {"max_iterations": 100})
    assert len(outcomes) == 1
    assert outcomes[0].layer == "numerical"
    assert outcomes[0].severity == Severity.WARNING
    assert "near iteration limit" in outcomes[0].messages[0]


def test_near_iteration_limit_warning_with_n_iterations_key() -> None:
    """The optimization-family skills (optimize_scalar/constrained,
    curve_fit) use n_iterations, not iterations."""
    outcomes = _validate({"n_iterations": 95}, {"max_iterations": 100})
    assert len(outcomes) == 1
    assert "near iteration limit" in outcomes[0].messages[0]


def test_exactly_at_90_percent_is_warning() -> None:
    outcomes = _validate({"iterations": 90}, {"max_iterations": 100})
    assert any("near iteration limit" in o.messages[0] for o in outcomes)


def test_below_90_percent_is_ok() -> None:
    outcomes = _validate({"iterations": 89}, {"max_iterations": 100})
    assert outcomes == []


def test_max_iterations_in_diagnostics_alone_does_not_fire() -> None:
    """Regression guard for the original bug: max_iterations living only
    in diagnostics (never true for any real skill, but was the original,
    dead code path) must not accidentally fire either."""
    outcomes = _validate({"iterations": 99, "max_iterations": 100})
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
    outcomes = _validate({"residual": 1e-3}, {"tolerance": 1e-6})
    assert len(outcomes) == 1
    assert outcomes[0].severity == Severity.WARNING
    assert "residual exceeds tolerance" in outcomes[0].messages[0]


def test_residual_exceeds_tolerance_reads_abs_error_key() -> None:
    """mathematics.integrate reports abs_error, not residual, and echoes
    tolerance into diagnostics rather than only accepting it as input."""
    outcomes = _validate({"abs_error": 1e-3, "tolerance": 1e-6})
    assert len(outcomes) == 1
    assert "residual exceeds tolerance" in outcomes[0].messages[0]


def test_residual_exceeds_tolerance_reads_residuals_list_max() -> None:
    """mathematics.curve_fit reports a residuals list, not one scalar --
    the worst (max absolute) residual is compared to tolerance."""
    outcomes = _validate({"residuals": [1e-9, -1e-3, 1e-9]}, {"tolerance": 1e-6})
    assert len(outcomes) == 1
    assert "residual exceeds tolerance" in outcomes[0].messages[0]


def test_residual_within_tolerance_ok() -> None:
    outcomes = _validate({"residual": 1e-9}, {"tolerance": 1e-6})
    assert outcomes == []


def test_negative_residual_uses_absolute_value() -> None:
    outcomes = _validate({"residual": -1e-3}, {"tolerance": 1e-6})
    assert len(outcomes) == 1
    assert outcomes[0].severity == Severity.WARNING


def test_multiple_warnings_are_all_reported() -> None:
    outcomes = _validate(
        {"iterations": 100, "condition_number": 1e12, "residual": 0.1},
        {"max_iterations": 100, "tolerance": 1e-6},
    )
    assert len(outcomes) == 3
    assert all(o.severity == Severity.WARNING for o in outcomes)
    messages = {o.messages[0] for o in outcomes}
    assert "near iteration limit" in messages
    assert "poorly conditioned" in messages
    assert "residual exceeds tolerance" in messages


def test_layer_class_attribute() -> None:
    assert NumericalDiagnosticsValidator.layer == "numerical"
