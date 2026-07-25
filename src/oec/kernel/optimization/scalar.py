"""Scalar minimization wrappers over SciPy (plan section 14.x: ``math.optimize_scalar``).

Method selection is explicit, never silent (plan section 4.4): the
caller states ``method`` directly, or a documented default is applied
based on whether ``bounds`` were given — see
:func:`select_default_method`. SciPy's ``bounded`` method is the only
one of the three that accepts ``bounds``; passing both a method other
than ``bounded`` and a ``bounds`` argument is a malformed call, not a
silently-ignored bound.

Diagnostics are always returned in the same shape
(:class:`~oec.kernel.optimization.diagnostics.OptimizationDiagnostics`),
mirroring ``root_finding.py``'s pattern so ``compute_status`` (ADR 0007)
and ``ExecutionService`` (ADR 0013) treat every optimization skill the
same way: read ``converged``, done.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

import scipy.optimize
from pydantic import BaseModel, ConfigDict

from oec.errors import NumericalDomainError
from oec.kernel.optimization.diagnostics import OptimizationDiagnostics

ScalarMethod = Literal["bounded", "brent", "golden"]

_METHODS: frozenset[str] = frozenset({"bounded", "brent", "golden"})


class ScalarOptimizationResult(BaseModel):
    """A scalar-minimization call's outcome: the minimizer and how it was found."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    x: float
    fun: float
    diagnostics: OptimizationDiagnostics


def select_default_method(*, has_bounds: bool) -> ScalarMethod:
    """The documented, explicit method-selection rule (plan section 4.4).

    Bounds select SciPy's ``bounded`` (Brent restricted to an interval —
    the only one of the three methods that accepts ``bounds`` at all).
    No bounds select unconstrained ``brent``; ``golden`` remains
    available but only on explicit request.
    """
    return "bounded" if has_bounds else "brent"


def minimize_scalar(
    f: Callable[[float], float],
    *,
    bounds: tuple[float, float] | None = None,
    method: ScalarMethod | None = None,
    tolerance: float | None = None,
    max_iterations: int | None = None,
) -> ScalarOptimizationResult:
    """Minimize a scalar function of one variable.

    Raises :class:`~oec.errors.NumericalDomainError` for a malformed
    call: an unrecognized ``method``, ``bounds`` given together with a
    method other than ``bounded``, ``bounded`` requested without
    ``bounds``, or a degenerate bracket/bounds pair SciPy itself
    rejects. Non-convergence within ``max_iterations`` is *not* raised;
    it comes back as ``diagnostics.converged is False``, per ADR 0007.
    """
    resolved_method = method or select_default_method(has_bounds=bounds is not None)
    if resolved_method not in _METHODS:
        raise NumericalDomainError(
            f"unknown scalar optimization method {resolved_method!r}",
            details={"method": resolved_method, "allowed": sorted(_METHODS)},
        )
    if resolved_method == "bounded" and bounds is None:
        raise NumericalDomainError(
            "method='bounded' requires 'bounds'",
            details={"method": resolved_method},
        )
    if resolved_method != "bounded" and bounds is not None:
        raise NumericalDomainError(
            f"'bounds' is only accepted with method='bounded', got method={resolved_method!r}",
            details={"method": resolved_method},
        )

    options: dict[str, Any] = {}
    if max_iterations is not None:
        options["maxiter"] = max_iterations

    kwargs: dict[str, Any] = {"method": resolved_method, "options": options}
    if bounds is not None:
        kwargs["bounds"] = bounds
    if tolerance is not None:
        kwargs["tol"] = tolerance

    try:
        outcome = scipy.optimize.minimize_scalar(f, **kwargs)
    except ValueError as exc:
        raise NumericalDomainError(
            f"invalid scalar optimization call: {exc}",
            details={"method": resolved_method, "bounds": bounds},
        ) from exc

    return ScalarOptimizationResult(
        x=float(outcome.x),
        fun=float(outcome.fun),
        diagnostics=OptimizationDiagnostics(
            method=resolved_method,
            converged=bool(outcome.success),
            message=str(outcome.message),
            n_iterations=int(outcome.nit),
            n_function_evaluations=int(outcome.nfev),
        ),
    )
