"""Multi-variable, box- and nonlinearly-constrained minimization wrappers
over SciPy (plan section 14.x: ``math.optimize_constrained``).

Method selection is explicit, never silent (plan section 4.4): SLSQP is
the documented default (handles bounds and general equality/inequality
constraints together, SciPy's traditional workhorse for this problem
class); ``trust-constr`` is available as an explicit alternative — it
natively reports ``optimality``/``constr_violation`` (an interior-point
method's own convergence measures), which SLSQP does not compute at
all. Rather than fabricate a number SLSQP never measured, this module
reports SciPy's *native* value when the chosen method provides one, and
falls back to evaluating the constraint functions directly at the
solution otherwise — see :func:`minimize_constrained` and
:func:`_evaluate_constraint_violation`.

Diagnostics are always returned in the same shape
(:class:`~oec.kernel.optimization.diagnostics.OptimizationDiagnostics`),
mirroring ``scalar.py``'s pattern.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import scipy.optimize
from pydantic import BaseModel, ConfigDict

from oec.errors import NumericalDomainError
from oec.kernel.optimization.diagnostics import OptimizationDiagnostics

ConstrainedMethod = Literal["SLSQP", "trust-constr"]
ConstraintKind = Literal["eq", "ineq"]

_METHODS: frozenset[str] = frozenset({"SLSQP", "trust-constr"})
_CONSTRAINT_KINDS: frozenset[str] = frozenset({"eq", "ineq"})

# How close a SciPy-reported ineq/eq constraint value has to be to
# "satisfied" (0 for eq, >= 0 for ineq) to call the point feasible, when
# this module has to compute the violation itself (SLSQP; see module
# docstring). Matches the loose end of SciPy's own default constraint
# tolerances (`SLSQP`'s ftol-adjacent default is 1e-6).
_FEASIBILITY_TOLERANCE = 1e-6


@dataclass(frozen=True)
class Constraint:
    """One nonlinear constraint: ``fun(x) == 0`` if ``kind == "eq"``,
    ``fun(x) >= 0`` if ``kind == "ineq"`` — SciPy's own convention."""

    kind: ConstraintKind
    fun: Callable[[Sequence[float]], float]


class ConstrainedOptimizationResult(BaseModel):
    """A constrained-minimization call's outcome: the minimizer and how it was found."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    x: list[float]
    fun: float
    diagnostics: OptimizationDiagnostics


def select_default_method() -> ConstrainedMethod:
    """The documented, explicit method-selection rule (plan section 4.4).

    SLSQP is the default for every call, regardless of whether bounds or
    constraints are present — it handles the unconstrained, bounds-only,
    and fully-constrained cases uniformly. ``trust-constr`` is never
    auto-selected; a caller picks it explicitly to get its native
    ``optimality``/``constraint_violation`` diagnostics.
    """
    return "SLSQP"


def minimize_constrained(
    f: Callable[[Sequence[float]], float],
    x0: Sequence[float],
    *,
    bounds: Sequence[tuple[float | None, float | None]] | None = None,
    constraints: Sequence[Constraint] = (),
    method: ConstrainedMethod | None = None,
    tolerance: float | None = None,
    max_iterations: int | None = None,
) -> ConstrainedOptimizationResult:
    """Minimize a scalar-valued function of several variables.

    Raises :class:`~oec.errors.NumericalDomainError` for a malformed
    call: an unrecognized ``method``, an unrecognized constraint
    ``kind``, or ``bounds`` whose length doesn't match ``x0``.
    Non-convergence / an infeasible result within ``max_iterations`` is
    *not* raised; it comes back as ``diagnostics.converged is False`` or
    ``diagnostics.feasible is False``, per ADR 0007.
    """
    resolved_method = method or select_default_method()
    if resolved_method not in _METHODS:
        raise NumericalDomainError(
            f"unknown constrained optimization method {resolved_method!r}",
            details={"method": resolved_method, "allowed": sorted(_METHODS)},
        )
    for constraint in constraints:
        if constraint.kind not in _CONSTRAINT_KINDS:
            raise NumericalDomainError(
                f"unknown constraint kind {constraint.kind!r}",
                details={"kind": constraint.kind, "allowed": sorted(_CONSTRAINT_KINDS)},
            )
    if bounds is not None and len(bounds) != len(x0):
        raise NumericalDomainError(
            f"'bounds' has {len(bounds)} entries but x0 has {len(x0)}",
            details={"n_bounds": len(bounds), "n_x0": len(x0)},
        )

    options: dict[str, Any] = {}
    if max_iterations is not None:
        options["maxiter"] = max_iterations

    kwargs: dict[str, Any] = {
        "method": resolved_method,
        "bounds": bounds,
        "constraints": [{"type": c.kind, "fun": c.fun} for c in constraints],
        "options": options,
    }
    if tolerance is not None:
        kwargs["tol"] = tolerance

    def _objective(v: np.ndarray) -> float:
        # scipy calls `fun` with an ndarray; f's own signature is the
        # wider Sequence[float] (an ndarray satisfies that at runtime,
        # but scipy-stubs types `fun` as taking an ndarray specifically),
        # so this thin adapter is what actually matches scipy's stub.
        return f(v.tolist())

    try:
        outcome = scipy.optimize.minimize(_objective, x0=np.asarray(x0, dtype=float), **kwargs)
    except ValueError as exc:
        raise NumericalDomainError(
            f"invalid constrained optimization call: {exc}",
            details={"method": resolved_method},
        ) from exc

    x_star = [float(v) for v in np.atleast_1d(outcome.x)]
    constraint_violation, feasible = _evaluate_constraint_violation(x_star, outcome, constraints)

    native_optimality = getattr(outcome, "optimality", None)

    return ConstrainedOptimizationResult(
        x=x_star,
        fun=float(outcome.fun),
        diagnostics=OptimizationDiagnostics(
            method=resolved_method,
            converged=bool(outcome.success),
            message=str(outcome.message),
            n_iterations=int(outcome.nit),
            n_function_evaluations=int(outcome.nfev),
            optimality=float(native_optimality) if native_optimality is not None else None,
            constraint_violation=constraint_violation,
            feasible=feasible,
        ),
    )


def _evaluate_constraint_violation(
    x: Sequence[float],
    outcome: scipy.optimize.OptimizeResult,
    constraints: Sequence[Constraint],
) -> tuple[float | None, bool | None]:
    """Prefer SciPy's own ``constr_violation`` (``trust-constr`` computes
    it natively); SLSQP reports nothing of the kind, so fall back to
    evaluating each constraint function at the solution directly. With
    no constraints at all, there is nothing to violate: SLSQP reports
    ``(None, None)`` (never measured anything), while trust-constr's own
    ``constr_violation`` of 0.0 is still honored as "feasible" — both
    reflect what that method actually did, not a fabricated agreement
    between the two.
    """
    native_violation = getattr(outcome, "constr_violation", None)
    if native_violation is not None:
        violation = float(native_violation)
        return violation, violation <= _FEASIBILITY_TOLERANCE

    if not constraints:
        return None, None

    violations = [abs(c.fun(x)) if c.kind == "eq" else max(0.0, -c.fun(x)) for c in constraints]
    max_violation = max(violations)
    return max_violation, max_violation <= _FEASIBILITY_TOLERANCE
