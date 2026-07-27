"""Finite-difference numerical differentiation — new under
``kernel/computational`` (ADR 0022). Scalar-to-scalar only for v0
(gradient/Jacobian for vector-valued functions is a non-goal this pass).

``scipy.misc.derivative`` (the function that used to fit this need) was
removed from modern SciPy; ``scipy.optimize.approx_fprime`` only does
forward differences with no step control suited to a general
derivative-at-a-point primitive. A small, auditable central/forward/
backward finite-difference implementation is the right-sized choice here —
not a reimplementation of existing SciPy/NumPy functionality, since
nothing suitable remains to wrap.

Not iterative: ``diagnostics.converged`` is always ``None`` (ADR 0013),
same convention as interpolation and tabulated integration.
"""

from __future__ import annotations

import math
from collections.abc import Callable
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
