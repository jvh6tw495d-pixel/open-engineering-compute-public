"""Finite-difference numerical differentiation — under
``kernel/computational`` (ADR 0022).

Scalar first derivative (v0) plus multi-variable Jacobian (W1) via the same
central/forward/backward finite-difference stencils. SciPy no longer ships a
general scalar ``derivative`` helper; OEC keeps a small auditable FD kernel.

Not iterative: ``diagnostics.converged`` is always ``None`` (ADR 0013),
same convention as interpolation and tabulated integration.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict

from oec.errors import NumericalDomainError
from oec.kernel.computational.diagnostics import ComputationalDiagnostics

DifferentiationMethod = Literal["central", "forward", "backward"]

# Standard finite-difference step-size formulas balancing truncation error
# against floating-point roundoff: central difference has O(h^2) truncation
# error, minimized against O(eps/h) roundoff at h ~ eps**(1/3); forward/
# backward have O(h) truncation error, minimized at h ~ eps**(1/2).
_MACHINE_EPS = math.ulp(1.0)
_CENTRAL_STEP_ORDER = 1.0 / 3.0
_ONE_SIDED_STEP_ORDER = 1.0 / 2.0


class DifferentiationResult(BaseModel):
    """A numerical derivative at a point, and the step size actually used."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float
    diagnostics: ComputationalDiagnostics


def differentiate(
    f: Callable[[float], float],
    x: float,
    *,
    method: DifferentiationMethod = "central",
    step: float | None = None,
) -> DifferentiationResult:
    """The first derivative of ``f`` at ``x`` via finite differences.

    Raises :class:`~oec.errors.NumericalDomainError` for a non-positive
    ``step`` or an unrecognized ``method`` — malformed calls, not solver
    outcomes.
    """
    if step is not None and step <= 0:
        raise NumericalDomainError(f"step must be positive, got {step!r}", details={"step": step})

    if method == "central":
        h = step if step is not None else _default_step(x, order=_CENTRAL_STEP_ORDER)
        derivative = (f(x + h) - f(x - h)) / (2.0 * h)
    elif method == "forward":
        h = step if step is not None else _default_step(x, order=_ONE_SIDED_STEP_ORDER)
        derivative = (f(x + h) - f(x)) / h
    elif method == "backward":
        h = step if step is not None else _default_step(x, order=_ONE_SIDED_STEP_ORDER)
        derivative = (f(x) - f(x - h)) / h
    else:
        raise NumericalDomainError(
            f"unknown differentiation method {method!r}", details={"method": method}
        )

    return DifferentiationResult(
        value=float(derivative),
        diagnostics=ComputationalDiagnostics(
            method=method,
            backend="oec",
            converged=None,
            step=h,
        ),
    )


def _default_step(x: float, *, order: float) -> float:
    """The adaptive finite-difference step ``h = max(|x|, 1) * eps**order``."""
    return float(max(abs(x), 1.0) * (_MACHINE_EPS**order))


class JacobianResult(BaseModel):
    """Jacobian matrix (m functions × n variables) via finite differences."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    jacobian: list[list[float]]
    point: list[float]
    variables: list[str]
    diagnostics: ComputationalDiagnostics


def jacobian(
    functions: Sequence[Callable[[Sequence[float]], float]],
    point: Sequence[float],
    *,
    variables: Sequence[str] | None = None,
    method: DifferentiationMethod = "central",
    step: float | None = None,
) -> JacobianResult:
    """Approximate Jacobian J[i,j] = ∂f_i / ∂x_j at ``point``.

    Each callable receives the full variable vector. Raises
    :class:`~oec.errors.NumericalDomainError` for empty functions/point or
    invalid method/step.
    """
    if not functions:
        raise NumericalDomainError("functions must be non-empty")
    if not point:
        raise NumericalDomainError("point must be non-empty")
    if step is not None and step <= 0:
        raise NumericalDomainError(f"step must be positive, got {step!r}", details={"step": step})
    if method not in {"central", "forward", "backward"}:
        raise NumericalDomainError(
            f"unknown differentiation method {method!r}", details={"method": method}
        )

    x0 = [float(v) for v in point]
    n = len(x0)
    names = list(variables) if variables is not None else [f"x{i}" for i in range(n)]
    if len(names) != n:
        raise NumericalDomainError(
            f"variables length {len(names)} must match point length {n}",
            details={"variables": names, "point": x0},
        )

    order = _CENTRAL_STEP_ORDER if method == "central" else _ONE_SIDED_STEP_ORDER
    steps = [step if step is not None else _default_step(xi, order=order) for xi in x0]

    rows: list[list[float]] = []
    for f in functions:
        row: list[float] = []
        for j in range(n):
            h = steps[j]
            if method == "central":
                xp = list(x0)
                xm = list(x0)
                xp[j] = x0[j] + h
                xm[j] = x0[j] - h
                deriv = (float(f(xp)) - float(f(xm))) / (2.0 * h)
            elif method == "forward":
                xp = list(x0)
                xp[j] = x0[j] + h
                deriv = (float(f(xp)) - float(f(x0))) / h
            else:  # backward
                xm = list(x0)
                xm[j] = x0[j] - h
                deriv = (float(f(x0)) - float(f(xm))) / h
            row.append(float(deriv))
        rows.append(row)

    return JacobianResult(
        jacobian=rows,
        point=x0,
        variables=names,
        diagnostics=ComputationalDiagnostics(
            method=method,
            backend="oec",
            converged=None,
            step=float(min(steps)) if steps else None,
        ),
    )
