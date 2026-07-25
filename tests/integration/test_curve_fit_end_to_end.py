"""End-to-end: mathematics.curve_fit through the real, sandboxed
ExecutionService -- registry -> validators -> subprocess -> status ->
provenance. Mirrors ``test_optimize_scalar_end_to_end.py``.
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
_CURVE_FIT_DIR = _SKILLS_ROOT / "mathematics" / "curve_fit"
_CurveFitValidator = load_skill_module(_CURVE_FIT_DIR, "validation").CurveFitValidator


def _service() -> ExecutionService:
    registry = SkillRegistry()
    report = registry.register_all(_SKILLS_ROOT)
    assert not report.failures, f"skill(s) failed to load: {report.failures}"
    return ExecutionService(
        registry,
        input_validators=[SchemaValidator(), _CurveFitValidator()],
        result_validators=[InvariantValidator(), NumericalDiagnosticsValidator()],
    )


def test_curve_fit_linear_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.curve_fit",
            inputs={
                "model": "a*x + b",
                "parameter_names": ["a", "b"],
                "x": [0.0, 1.0, 2.0, 3.0, 4.0],
                "y": [1.0, 3.0, 5.0, 7.0, 9.0],
                "initial_guess": [1.0, 1.0],
            },
        )
    )

    # iterative:true + converged + no warnings -> VALIDATED
    assert result.status is ExecutionStatus.VALIDATED
    assert math.isclose(result.result["params"][0], 2.0, abs_tol=1e-6)
    assert math.isclose(result.result["params"][1], 1.0, abs_tol=1e-6)
    assert result.result["method"] == "lm"
    assert result.diagnostics["converged"] is True


def test_curve_fit_schema_violation_is_invalid_without_executing() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.curve_fit",
            inputs={
                "model": "a*x",
                "parameter_names": ["a"],
                "x": [0.0, 1.0],
                "y": [0.0, 1.0],
                "initial_guess": [1.0],
                "unexpected_field": True,
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_curve_fit_x_y_length_mismatch_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.curve_fit",
            inputs={
                "model": "a*x",
                "parameter_names": ["a"],
                "x": [0.0, 1.0, 2.0],
                "y": [0.0, 1.0],
                "initial_guess": [1.0],
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID
