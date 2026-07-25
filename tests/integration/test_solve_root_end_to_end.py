"""End-to-end: mathematics.solve_root through the real, sandboxed
ExecutionService -- the first real MVP skill (plan section 14.1)
exercised through the whole pipeline (registry -> validators -> subprocess
-> status -> provenance), not a loader/registry test fixture.

Note the explicit ``SolveRootValidator`` in the input validator list:
``ExecutionService`` does not yet auto-discover a skill's own
``validation.py`` from its manifest -- whoever constructs the service
for a given skill must know to include that skill's validators. This is
a known, documented gap (see ``docs/development/codebase-map.md``), not
an oversight; deferred until more skills exist to inform what the
auto-wiring convention should actually look like.
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
_SOLVE_ROOT_DIR = _SKILLS_ROOT / "mathematics" / "solve_root"
_SolveRootValidator = load_skill_module(_SOLVE_ROOT_DIR, "validation").SolveRootValidator


def _service() -> ExecutionService:
    registry = SkillRegistry()
    report = registry.register_all(_SKILLS_ROOT)
    assert not report.failures, f"skill(s) failed to load: {report.failures}"
    return ExecutionService(
        registry,
        input_validators=[SchemaValidator(), _SolveRootValidator()],
        result_validators=[InvariantValidator(), NumericalDiagnosticsValidator()],
    )


def test_solve_root_bracketed_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.solve_root",
            inputs={"expression": "x**2 - 2", "bracket": [0, 2]},
        )
    )

    assert result.status is ExecutionStatus.VALIDATED
    assert math.isclose(result.result["root"], math.sqrt(2), rel_tol=1e-9)
    assert result.result["method"] == "brentq"
    assert result.diagnostics["converged"] is True


def test_solve_root_schema_violation_is_invalid_without_executing() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.solve_root",
            inputs={"expression": "x**2 - 2", "bracket": [0, 2], "unexpected_field": True},
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_solve_root_bad_bracket_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.solve_root",
            inputs={"expression": "x**2 - 2", "bracket": [0, 1]},
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_solve_root_missing_locator_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(skill_id="mathematics.solve_root", inputs={"expression": "x**2 - 2"})
    )
    assert result.status is ExecutionStatus.INVALID
