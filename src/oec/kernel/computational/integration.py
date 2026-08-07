"""Quadrature — unified under ``kernel/computational`` (ADR 0022). Moved
out of ``skills/mathematics/integrate/implementation.py``; same two modes
(adaptive function quadrature via QUADPACK, tabulated Simpson/trapezoid),
same convergence signal, no behavior change.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict
from scipy.integrate import quad, simpson, trapezoid

from oec.kernel.computational.diagnostics import ComputationalDiagnostics

TabulatedMethod = Literal["simpson", "trapezoid"]

# SciPy quad defaults (kept explicit so diagnostics/convergence use the
# same numbers that were actually passed to the solver).
DEFAULT_EPSABS = 1.49e-08
DEFAULT_EPSREL = 1.49e-08


class IntegrationResult(BaseModel):
    """A definite integral's value, from either integration mode."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float
    mode: Literal["function", "tabulated"]
    diagnostics: ComputationalDiagnostics


def integrate_function(
    f: Callable[[float], float],
    a: float,
    b: float,
    *,
    epsabs: float = DEFAULT_EPSABS,
    epsrel: float = DEFAULT_EPSREL,
) -> IntegrationResult:
    """Adaptive quadrature of ``f`` over ``[a, b]`` via QUADPACK (SciPy ``quad``)."""
    quad_result = quad(f, a, b, epsabs=epsabs, epsrel=epsrel, full_output=True)
    value = float(quad_result[0])
    abs_error = float(quad_result[1])
    # QUADPACK returns a 4th element (a human-readable explanation) only
    # when it hit a real problem (subdivision limit, slow convergence, a
    # suspected singularity, ...). Its *absence* is the authoritative
    # convergence signal -- comparing abs_error to the requested tolerance
    # alone is not: abs_error is QUADPACK's own estimate, which can look
    # deceptively small for the exact integrand that triggers the warning.
    quadpack_reported_a_problem = len(quad_result) > 3
    tolerance = max(epsabs, epsrel * abs(value))
    converged = not quadpack_reported_a_problem and abs_error <= tolerance

    extra: dict[str, Any] = {
        "abs_error": abs_error,
        "epsabs": epsabs,
        "epsrel": epsrel,
        "tolerance": tolerance,
        "n_evaluations": int(quad_result[2]["neval"]),
    }
    if quadpack_reported_a_problem:
        # scipy-stubs' overload for full_output=True declares a fixed
        # 3-tuple; QUADPACK actually appends a 4th element (explanation
        # string) only when it reports a problem, which is exactly the
        # branch guarded by the runtime len() check above.
        extra["quadpack_message"] = str(quad_result[3])  # type: ignore[misc]

    return IntegrationResult(
        value=value,
        mode="function",
        diagnostics=ComputationalDiagnostics(
            method="adaptive_quad", backend="scipy", converged=converged, **extra
        ),
    )


def integrate_tabulated(
    x: Sequence[float], y: Sequence[float], *, method: TabulatedMethod | None = None
) -> IntegrationResult:
    """Fixed closed-form quadrature (Simpson or trapezoid) over tabulated data.

    Not iterative: ``diagnostics.converged`` is always ``None``, distinct
    from ``False`` (ADR 0013 amendment) -- a present-but-null value means
    "this specific call was exact," eligible for VERIFIED just like an
    interpolation result, not held to the weaker VALIDATED tier just
    because :func:`integrate_function` (the other mode) is adaptive.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    resolved_method = _select_tabulated_method(method, n_points=int(x_arr.size))

    value = (
        float(simpson(y_arr, x=x_arr))
        if resolved_method == "simpson"
        else float(trapezoid(y_arr, x=x_arr))
    )

    return IntegrationResult(
        value=value,
        mode="tabulated",
        diagnostics=ComputationalDiagnostics(
            method=resolved_method,
            backend="scipy",
            converged=None,
            n_points=int(x_arr.size),
        ),
    )


def _select_tabulated_method(requested: str | None, *, n_points: int) -> TabulatedMethod:
    """Mirror the documented rule in ``mathematics.integrate``'s skill.md."""
    if requested == "trapezoid":
        return "trapezoid"
    if requested == "simpson":
        return "simpson"
    # Auto-select: Simpson needs >= 3 samples; 2-point data -> trapezoid.
    if n_points >= 3:
        return "simpson"
    return "trapezoid"
