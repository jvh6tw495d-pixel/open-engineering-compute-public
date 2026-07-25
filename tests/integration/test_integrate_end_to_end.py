"""End-to-end: mathematics.integrate through the real, sandboxed
ExecutionService — registry -> validators -> subprocess -> status ->
provenance. Mirrors ``test_solve_root_end_to_end.py``.

Note the explicit ``IntegrateValidator`` in the input validator list:
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
_INTEGRATE_DIR = _SKILLS_ROOT / "mathematics" / "integrate"
_IntegrateValidator = load_skill_module(_INTEGRATE_DIR, "validation").IntegrateValidator


def _service() -> ExecutionService:
    registry = SkillRegistry()
    report = registry.register_all(_SKILLS_ROOT)
    assert not report.failures, f"skill(s) failed to load: {report.failures}"
    return ExecutionService(
        registry,
        input_validators=[SchemaValidator(), _IntegrateValidator()],
        result_validators=[InvariantValidator(), NumericalDiagnosticsValidator()],
    )


def test_integrate_function_sin_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.integrate",
            inputs={"expression": "sin(x)", "bounds": [0.0, math.pi]},
        )
    )

    # iterative:true + converged + no warnings → VALIDATED
    assert result.status is ExecutionStatus.VALIDATED
    assert math.isclose(result.result["value"], 2.0, rel_tol=1e-9, abs_tol=1e-9)
    assert result.result["mode"] == "function"
    assert result.diagnostics["converged"] is True
    assert result.diagnostics["method"] == "adaptive_quad"


def test_integrate_tabulated_simpson_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.integrate",
            inputs={
                "x": [0.0, 0.25, 0.5, 0.75, 1.0],
                "y": [0.0, 0.0625, 0.25, 0.5625, 1.0],
            },
        )
    )
    # Tabulated mode is exact -- ADR 0013 amendment: a present-but-null
    # `converged` is eligible for VERIFIED, not held to VALIDATED just
    # because the skill also has an adaptive function mode.
    assert result.status is ExecutionStatus.VERIFIED
    assert math.isclose(result.result["value"], 1.0 / 3.0, rel_tol=1e-9, abs_tol=1e-9)
    assert result.result["mode"] == "tabulated"
    assert result.diagnostics["converged"] is None
    assert result.diagnostics["method"] == "simpson"


def test_integrate_schema_violation_is_invalid_without_executing() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.integrate",
            inputs={
                "expression": "x",
                "bounds": [0.0, 1.0],
                "unexpected_field": True,
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_integrate_both_modes_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.integrate",
            inputs={
                "expression": "x",
                "bounds": [0.0, 1.0],
                "x": [0.0, 1.0],
                "y": [0.0, 1.0],
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_integrate_missing_mode_is_invalid() -> None:
    service = _service()
    result = service.execute(ExecutionRequest(skill_id="mathematics.integrate", inputs={}))
    assert result.status is ExecutionStatus.INVALID


def test_integrate_bad_expression_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.integrate",
            inputs={"expression": "x +", "bounds": [0.0, 1.0]},
        )
    )
    assert result.status is ExecutionStatus.INVALID
