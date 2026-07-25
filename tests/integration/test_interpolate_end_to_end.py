"""End-to-end: mathematics.interpolate through the real, sandboxed
ExecutionService — registry -> validators -> subprocess -> status ->
provenance. Mirrors ``test_solve_root_end_to_end.py``.

Note the explicit ``InterpolateValidator`` in the input validator list:
``ExecutionService`` does not yet auto-discover a skill's own
``validation.py`` from its manifest — whoever constructs the service
for a given skill must know to include that skill's validators. This is
a known, documented gap (see ``docs/development/codebase-map.md``).
"""

import math
from pathlib import Path

from oec.execution.models import ExecutionRequest, ExecutionStatus
from oec.execution.service import ExecutionService
from oec.skills.registry.registry import SkillRegistry
from oec.testing import load_skill_module
from oec.validation.invariants import InvariantValidator
from oec.validation.numerical import NumericalDiagnosticsValidator
from oec.validation.schema import SchemaValidator

_SKILLS_ROOT = Path("skills")
_INTERPOLATE_DIR = _SKILLS_ROOT / "mathematics" / "interpolate"
_InterpolateValidator = load_skill_module(_INTERPOLATE_DIR, "validation").InterpolateValidator


def _service() -> ExecutionService:
    registry = SkillRegistry()
    report = registry.register_all(_SKILLS_ROOT)
    assert not report.failures, f"skill(s) failed to load: {report.failures}"
    return ExecutionService(
        registry,
        input_validators=[SchemaValidator(), _InterpolateValidator()],
        result_validators=[InvariantValidator(), NumericalDiagnosticsValidator()],
    )


def test_interpolate_linear_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.interpolate",
            inputs={
                "x": [0.0, 1.0, 2.0, 3.0],
                "y": [0.0, 2.0, 4.0, 6.0],
                "query_points": [0.5, 1.5, 2.5],
                "method": "linear",
            },
        )
    )

    # iterative:false + no warnings → VERIFIED (exact/closed-form path)
    assert result.status is ExecutionStatus.VERIFIED
    assert result.result["values"] == [1.0, 3.0, 5.0]
    assert result.diagnostics["method"] == "linear"
    assert "converged" not in result.diagnostics


def test_interpolate_cubic_spline_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.interpolate",
            inputs={
                "x": [0.0, 1.0, 2.0, 3.0, 4.0],
                "y": [0.0, 1.0, 8.0, 27.0, 64.0],
                "query_points": [0.5, 1.5, 2.5, 3.5],
                "method": "cubic_spline",
            },
        )
    )
    assert result.status is ExecutionStatus.VERIFIED
    expected = [0.125, 3.375, 15.625, 42.875]
    assert len(result.result["values"]) == len(expected)
    for actual, exp in zip(result.result["values"], expected, strict=True):
        assert math.isclose(actual, exp, rel_tol=1e-9, abs_tol=1e-9)


def test_interpolate_schema_violation_is_invalid_without_executing() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.interpolate",
            inputs={
                "x": [0.0, 1.0],
                "y": [0.0, 1.0],
                "query_points": [0.5],
                "method": "linear",
                "unexpected_field": True,
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_interpolate_non_increasing_x_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.interpolate",
            inputs={
                "x": [0.0, 2.0, 1.0],
                "y": [0.0, 1.0, 0.0],
                "query_points": [0.5],
                "method": "linear",
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_interpolate_extrapolation_is_converged_with_warnings() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.interpolate",
            inputs={
                "x": [0.0, 1.0, 2.0],
                "y": [0.0, 1.0, 0.0],
                "query_points": [-1.0, 0.5],
                "method": "linear",
            },
        )
    )
    assert result.status is ExecutionStatus.CONVERGED_WITH_WARNINGS
    assert len(result.result["values"]) == 2


def test_interpolate_missing_method_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.interpolate",
            inputs={
                "x": [0.0, 1.0],
                "y": [0.0, 1.0],
                "query_points": [0.5],
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID
