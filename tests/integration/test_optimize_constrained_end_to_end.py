"""End-to-end: mathematics.optimize_constrained through the real,
sandboxed ExecutionService -- registry -> validators -> subprocess ->
status -> provenance. Mirrors ``test_optimize_scalar_end_to_end.py``.
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
_OPTIMIZE_CONSTRAINED_DIR = _SKILLS_ROOT / "mathematics" / "optimize_constrained"
_OptimizeConstrainedValidator = load_skill_module(
    _OPTIMIZE_CONSTRAINED_DIR, "validation"
).OptimizeConstrainedValidator


def _service() -> ExecutionService:
    registry = SkillRegistry()
    report = registry.register_all(_SKILLS_ROOT)
    assert not report.failures, f"skill(s) failed to load: {report.failures}"
    return ExecutionService(
        registry,
        input_validators=[SchemaValidator(), _OptimizeConstrainedValidator()],
        result_validators=[InvariantValidator(), NumericalDiagnosticsValidator()],
    )


def test_optimize_constrained_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.optimize_constrained",
            inputs={
                "variables": ["x", "y"],
                "expression": "x**2 + y**2",
                "x0": [0.0, 0.0],
                "bounds": [[-10, 10], [-10, 10]],
                "constraints": [{"type": "ineq", "expression": "x + y - 1"}],
            },
        )
    )

    # iterative:true + converged + no warnings -> VALIDATED
    assert result.status is ExecutionStatus.VALIDATED
    assert math.isclose(result.result["x"][0], 0.5, abs_tol=1e-6)
    assert math.isclose(result.result["x"][1], 0.5, abs_tol=1e-6)
    assert result.result["method"] == "SLSQP"
    assert result.diagnostics["converged"] is True


def test_optimize_constrained_schema_violation_is_invalid_without_executing() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.optimize_constrained",
            inputs={
                "variables": ["x"],
                "expression": "x**2",
                "x0": [0.0],
                "unexpected_field": True,
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_optimize_constrained_x0_length_mismatch_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.optimize_constrained",
            inputs={"variables": ["x", "y"], "expression": "x**2 + y**2", "x0": [0.0]},
        )
    )
    assert result.status is ExecutionStatus.INVALID
