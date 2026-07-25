"""End-to-end: mathematics.optimize_scalar through the real, sandboxed
ExecutionService -- registry -> validators -> subprocess -> status ->
provenance. Mirrors ``test_solve_root_end_to_end.py``, Sprint 05's
template skill for the ``oec.kernel.optimization`` family.
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
_OPTIMIZE_SCALAR_DIR = _SKILLS_ROOT / "mathematics" / "optimize_scalar"
_OptimizeScalarValidator = load_skill_module(
    _OPTIMIZE_SCALAR_DIR, "validation"
).OptimizeScalarValidator


def _service() -> ExecutionService:
    registry = SkillRegistry()
    report = registry.register_all(_SKILLS_ROOT)
    assert not report.failures, f"skill(s) failed to load: {report.failures}"
    return ExecutionService(
        registry,
        input_validators=[SchemaValidator(), _OptimizeScalarValidator()],
        result_validators=[InvariantValidator(), NumericalDiagnosticsValidator()],
    )


def test_optimize_scalar_bounded_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.optimize_scalar",
            inputs={"expression": "(x - 3)**2", "bounds": [0, 10], "method": "bounded"},
        )
    )

    # iterative:true + converged + no warnings -> VALIDATED
    assert result.status is ExecutionStatus.VALIDATED
    assert math.isclose(result.result["x"], 3.0, abs_tol=1e-6)
    assert math.isclose(result.result["fun"], 0.0, abs_tol=1e-9)
    assert result.result["method"] == "bounded"
    assert result.diagnostics["converged"] is True


def test_optimize_scalar_schema_violation_is_invalid_without_executing() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.optimize_scalar",
            inputs={"expression": "x**2", "bounds": [0, 1], "unexpected_field": True},
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_optimize_scalar_bounded_without_bounds_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.optimize_scalar",
            inputs={"expression": "x**2", "method": "bounded"},
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_optimize_scalar_inverted_bounds_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.optimize_scalar",
            inputs={"expression": "x**2", "bounds": [10, 0], "method": "bounded"},
        )
    )
    assert result.status is ExecutionStatus.INVALID
