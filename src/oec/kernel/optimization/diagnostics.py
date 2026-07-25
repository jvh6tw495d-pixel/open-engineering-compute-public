"""Shared diagnostics contract for the optimization kernel (Sprint 05).

One model, reused by every optimization skill (``math.optimize_scalar``,
``math.optimize_constrained``, ``math.curve_fit``), the same way
:class:`oec.kernel.numerics.root_finding.RootFindingDiagnostics` gives
``math.solve_root`` a single shape to report through. Fields that don't
apply to a given method are left ``None`` rather than fabricated —
scalar Brent has no constraint to violate, SLSQP does not report a
gradient-norm ``optimality`` the way ``trust-constr`` does, and only a
least-squares fit produces a ``covariance`` matrix. A caller must not
invent a value for a field its method cannot actually measure.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class OptimizationDiagnostics(BaseModel):
    """Solver diagnostics in the shape ``compute_status`` expects (ADR 0007/0013)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    method: str
    converged: bool
    message: str
    n_iterations: int
    n_function_evaluations: int
    optimality: float | None = None
    constraint_violation: float | None = None
    feasible: bool | None = None
    residuals: list[float] | None = None
    covariance: list[list[float]] | None = None
