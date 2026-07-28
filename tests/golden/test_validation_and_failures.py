"""Canonical "Validation and failures" golden set (v2.5 golden-set expansion,
docs/implementation/v2.5-golden-set-expansion.md).

Every case here drives the real, sandboxed ``ExecutionService`` end to end
(registry -> validators -> subprocess -> status -> provenance) -- the same
pattern as ``tests/integration/test_<skill>_end_to_end.py`` -- and asserts
the resulting :class:`~oec.execution.models.ExecutionStatus` for a known,
deliberately bad input. Nothing here is mocked or fixture-based: each case
exercises a real skill's real validators/kernel.

Sectioned by validation mechanism so the eight-domain v2.5 golden-set
distribution (OEC_V3_IMPLEMENTATION_PLAN.md §9) has one canonical bucket for
"Validação e falhas" rather than only scattered mechanism tests on fixtures.
Deliberately NOT attempted here (recorded as known gaps, not silently
dropped -- see the companion doc): ``ExecutionStatus.APPROXIMATE`` (no code
path sets it today), ``KalmanNumericalError``/``innovation_singular``, the
``invariants`` non-finite-output check, a genuinely-occurring ``FAILED`` on
a real (non-fixture) skill, and the verification engine's
``residuals_and_conditioning``/``backend_fit`` post-checks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oec.execution.factory import build_validators
from oec.execution.models import ExecutionRequest, ExecutionStatus
from oec.execution.service import ExecutionService
from oec.skills.registry.registry import SkillRegistry

_SKILLS_ROOT = Path("skills")


@pytest.fixture(scope="module")
def registry() -> SkillRegistry:
    reg = SkillRegistry()
    report = reg.register_all(_SKILLS_ROOT)
    assert not report.failures, f"skill(s) failed to load: {report.failures}"
    return reg


def _service(registry: SkillRegistry, skill_id: str) -> ExecutionService:
    skill = registry.get_skill(skill_id)
    input_validators, result_validators = build_validators(skill)
    return ExecutionService(
        registry, input_validators=input_validators, result_validators=result_validators
    )


# ---------------------------------------------------------------------------
# 1. Non-convergence -> INCONCLUSIVE (richest, easiest vein: each of these
#    inputs is already proven to yield diagnostics.converged=False at the
#    implementation.execute() level in the skill's own test_golden.py; here
#    the same input is driven through the full ExecutionService).
# ---------------------------------------------------------------------------


def test_curve_fit_low_max_iterations_is_inconclusive(registry: SkillRegistry) -> None:
    example = json.loads(
        (_SKILLS_ROOT / "mathematics/curve_fit/examples/sinusoid_exact_recovery.json").read_text(
            encoding="utf-8"
        )
    )
    service = _service(registry, "mathematics.curve_fit")
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.curve_fit",
            inputs={**example["input"], "max_iterations": 1},
        )
    )
    assert result.status is ExecutionStatus.INCONCLUSIVE
    assert result.diagnostics["converged"] is False


def test_integrate_oscillatory_near_zero_is_inconclusive(registry: SkillRegistry) -> None:
    """sin(1/x) near x=0 with an unattainable tolerance makes QUADPACK hit
    its subdivision limit -- a genuinely hard integrand, not a bug."""
    service = _service(registry, "mathematics.integrate")
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.integrate",
            inputs={
                "expression": "sin(1/x)",
                "bounds": [0.0001, 1.0],
                "epsabs": 1e-14,
                "epsrel": 1e-14,
            },
        )
    )
    assert result.status is ExecutionStatus.INCONCLUSIVE
    assert result.diagnostics["converged"] is False


def test_optimize_scalar_low_max_iterations_is_inconclusive(registry: SkillRegistry) -> None:
    service = _service(registry, "mathematics.optimize_scalar")
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.optimize_scalar",
            inputs={
                "expression": "(x - 3)**2",
                "bounds": [0, 10],
                "method": "bounded",
                "max_iterations": 1,
            },
        )
    )
    assert result.status is ExecutionStatus.INCONCLUSIVE
    assert result.diagnostics["converged"] is False


def test_optimize_constrained_contradictory_constraints_is_inconclusive(
    registry: SkillRegistry,
) -> None:
    """x+y<=0 and x+y>=1 cannot both hold -- a genuinely infeasible NLP,
    not an exception."""
    service = _service(registry, "mathematics.optimize_constrained")
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.optimize_constrained",
            inputs={
                "variables": ["x", "y"],
                "expression": "x**2 + y**2",
                "x0": [0.0, 0.0],
                "bounds": [[-10, 10], [-10, 10]],
                "constraints": [
                    {"type": "ineq", "expression": "-(x + y)"},
                    {"type": "ineq", "expression": "x + y - 1"},
                ],
            },
        )
    )
    assert result.status is ExecutionStatus.INCONCLUSIVE
    assert result.diagnostics["converged"] is False


def test_solve_root_low_max_iterations_is_inconclusive(registry: SkillRegistry) -> None:
    service = _service(registry, "mathematics.solve_root")
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.solve_root",
            inputs={"expression": "x**2 - 2", "bracket": [0, 2], "max_iterations": 1},
        )
    )
    assert result.status is ExecutionStatus.INCONCLUSIVE
    assert result.diagnostics["converged"] is False


# ---------------------------------------------------------------------------
# 2. Solver infeasibility -> INCONCLUSIVE (real HiGHS solve on a genuinely
#    infeasible LP topology).
# ---------------------------------------------------------------------------

highspy = pytest.importorskip("highspy")

_INFEASIBLE_LP_OPS = {
    "ops_version": "0.1.0",
    "problem_class": "lp",
    "sense": "min",
    "variables": [{"name": "x", "kind": "continuous", "lower": 0, "upper": 1}],
    "constraints": [{"name": "a", "coeffs": {"x": 1}, "sense": ">=", "rhs": 2}],
    "objective": {"coeffs": {"x": 1}},
}


def test_optimization_lp_infeasible_is_inconclusive(registry: SkillRegistry) -> None:
    """x in [0,1] with an added x>=2 constraint has no feasible point."""
    service = _service(registry, "optimization.lp")
    result = service.execute(
        ExecutionRequest(skill_id="optimization.lp", inputs={"ops": _INFEASIBLE_LP_OPS})
    )
    assert result.status is ExecutionStatus.INCONCLUSIVE
    assert result.result["solver_status"] == "infeasible"
    assert result.result["feasibility_issues"]


def test_check_feasibility_reports_infeasible_lp_as_inconclusive(
    registry: SkillRegistry,
) -> None:
    service = _service(registry, "optimization.check_feasibility")
    result = service.execute(
        ExecutionRequest(
            skill_id="optimization.check_feasibility", inputs={"ops": _INFEASIBLE_LP_OPS}
        )
    )
    assert result.status is ExecutionStatus.INCONCLUSIVE
    assert result.result["feasible"] is False


# ---------------------------------------------------------------------------
# 3. Linear-algebra domain validation -- validators/kernel already exist and
#    are unit-tested in isolation, but never driven end-to-end before now.
# ---------------------------------------------------------------------------


def test_solve_system_singular_matrix_reports_singular_not_an_exception(
    registry: SkillRegistry,
) -> None:
    """A=[[1,2],[2,4]] is exactly singular (det=0): solve_dense catches the
    LinAlgError and reports singular=True/converged=False in the result
    payload, not an exception. Note: linear.solve_system's manifest
    declares method.iterative=false (it's a direct LAPACK solve, not an
    iterative method), so per ADR 0007 the top-level ExecutionStatus
    stays VERIFIED regardless -- converged is only consulted for status
    on iterative methods. Callers must inspect result.diagnostics for
    this skill's own degenerate-input signal, not rely on status alone."""
    service = _service(registry, "linear.solve_system")
    result = service.execute(
        ExecutionRequest(
            skill_id="linear.solve_system",
            inputs={"A": [[1.0, 2.0], [2.0, 4.0]], "b": [1.0, 2.0]},
        )
    )
    assert result.status is ExecutionStatus.VERIFIED
    assert result.result["singular"] is True
    assert result.diagnostics["converged"] is False


def test_eig_non_square_matrix_is_invalid(registry: SkillRegistry) -> None:
    service = _service(registry, "linear.eig")
    result = service.execute(
        ExecutionRequest(
            skill_id="linear.eig",
            inputs={"A": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]},
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_least_squares_dimension_mismatch_is_invalid(registry: SkillRegistry) -> None:
    """A is 2x2 but b has length 3 -- len(b) must equal rows of A."""
    service = _service(registry, "linear.least_squares")
    result = service.execute(
        ExecutionRequest(
            skill_id="linear.least_squares",
            inputs={"A": [[1.0, 0.0], [0.0, 1.0]], "b": [1.0, 2.0, 3.0]},
        )
    )
    assert result.status is ExecutionStatus.INVALID


# ---------------------------------------------------------------------------
# 4. Physical validation -- battery.soc_step's validators exist but had zero
#    test coverage before this suite.
# ---------------------------------------------------------------------------

_VALID_SOC_STEP_INPUTS = {
    "soc": 0.5,
    "power": {"value": 100.0, "unit": "W"},
    "dt_hours": {"value": 1.0, "unit": "h"},
    "capacity": {"value": 1000.0, "unit": "Wh"},
}


def test_soc_step_soc_out_of_range_is_invalid(registry: SkillRegistry) -> None:
    service = _service(registry, "battery.soc_step")
    result = service.execute(
        ExecutionRequest(
            skill_id="battery.soc_step",
            inputs={**_VALID_SOC_STEP_INPUTS, "soc": 1.5},
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_soc_step_negative_capacity_is_invalid(registry: SkillRegistry) -> None:
    service = _service(registry, "battery.soc_step")
    result = service.execute(
        ExecutionRequest(
            skill_id="battery.soc_step",
            inputs={**_VALID_SOC_STEP_INPUTS, "capacity": {"value": -10.0, "unit": "Wh"}},
        )
    )
    assert result.status is ExecutionStatus.INVALID


# ---------------------------------------------------------------------------
# 5. Dimensional validation -- unit-family mismatches caught before
#    execution (ADR 0016 central normalization), not a solver/business rule.
# ---------------------------------------------------------------------------


def test_energy_balance_wrong_unit_family_is_invalid(registry: SkillRegistry) -> None:
    """energy_in declares x-oec-unit "Wh"; a value given in volts is a
    dimensional mismatch, not a numeric one -- schema alone can't reject
    it (type: number, unit: string are both individually satisfied)."""
    service = _service(registry, "energy.balance")
    result = service.execute(
        ExecutionRequest(
            skill_id="energy.balance",
            inputs={"energy_in": [{"value": 10.0, "unit": "V"}]},
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_soc_step_dt_hours_wrong_unit_family_is_invalid(registry: SkillRegistry) -> None:
    """dt_hours declares x-oec-unit "h"; a value given in watts is a
    dimensional mismatch on a different field than the energy_balance case
    above."""
    service = _service(registry, "battery.soc_step")
    result = service.execute(
        ExecutionRequest(
            skill_id="battery.soc_step",
            inputs={**_VALID_SOC_STEP_INPUTS, "dt_hours": {"value": 1.0, "unit": "W"}},
        )
    )
    assert result.status is ExecutionStatus.INVALID


# ---------------------------------------------------------------------------
# 6. Mathematical / expression domain validation -- cross-field checks JSON
#    Schema cannot express, already wired in each skill's own validation.py.
# ---------------------------------------------------------------------------


def test_optimize_constrained_undeclared_variable_is_invalid(registry: SkillRegistry) -> None:
    """'z' is not in the declared 'variables' list -- ExpressionError,
    caught by OptimizeConstrainedValidator before execution."""
    service = _service(registry, "mathematics.optimize_constrained")
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.optimize_constrained",
            inputs={
                "variables": ["x"],
                "expression": "x + z",
                "x0": [0.0],
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_solve_root_newton_without_derivative_is_invalid(registry: SkillRegistry) -> None:
    """method='newton' requires 'derivative' -- SolveRootValidator's
    cross-field check, not the kernel's NumericalDomainError (the skill
    never reaches the kernel with this input)."""
    service = _service(registry, "mathematics.solve_root")
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.solve_root",
            inputs={"expression": "x**2 - 2", "method": "newton", "initial_guess": 1.0},
        )
    )
    assert result.status is ExecutionStatus.INVALID


# ---------------------------------------------------------------------------
# 7. Schema validation -- additionalProperties:false / required-field
#    rejections, on skills not already covered by another skill's own
#    *_end_to_end.py file, so the mechanism has direct representation in
#    this dedicated bucket too.
# ---------------------------------------------------------------------------


def test_eig_schema_violation_is_invalid(registry: SkillRegistry) -> None:
    service = _service(registry, "linear.eig")
    result = service.execute(
        ExecutionRequest(
            skill_id="linear.eig",
            inputs={"A": [[1.0, 0.0], [0.0, 1.0]], "unexpected_field": True},
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_morris_schema_violation_is_invalid(registry: SkillRegistry) -> None:
    service = _service(registry, "uncertainty.morris")
    result = service.execute(
        ExecutionRequest(
            skill_id="uncertainty.morris",
            inputs={
                "bounds": [[0.0, 1.0]],
                "coeffs": [1.0],
                "unexpected_field": True,
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_regression_schema_violation_is_invalid(registry: SkillRegistry) -> None:
    service = _service(registry, "statistics.regression")
    result = service.execute(
        ExecutionRequest(
            skill_id="statistics.regression",
            inputs={
                "x": [[1.0, 0.0], [1.0, 1.0]],
                "y": [1.0, 2.0],
                "unexpected_field": True,
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_energy_balance_schema_violation_is_invalid(registry: SkillRegistry) -> None:
    service = _service(registry, "energy.balance")
    result = service.execute(
        ExecutionRequest(
            skill_id="energy.balance",
            inputs={
                "energy_in": [{"value": 10.0, "unit": "Wh"}],
                "unexpected_field": True,
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_optimization_lp_schema_violation_is_invalid(registry: SkillRegistry) -> None:
    service = _service(registry, "optimization.lp")
    result = service.execute(
        ExecutionRequest(
            skill_id="optimization.lp",
            inputs={"ops": _INFEASIBLE_LP_OPS, "unexpected_field": True},
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_soc_step_missing_required_field_is_invalid(registry: SkillRegistry) -> None:
    """'capacity' is required by input.schema.json; omitting it entirely
    is a missing-required-property schema violation, distinct in kind
    from the additionalProperties:false cases above."""
    service = _service(registry, "battery.soc_step")
    incomplete = {k: v for k, v in _VALID_SOC_STEP_INPUTS.items() if k != "capacity"}
    result = service.execute(ExecutionRequest(skill_id="battery.soc_step", inputs=incomplete))
    assert result.status is ExecutionStatus.INVALID
