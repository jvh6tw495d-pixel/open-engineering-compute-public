"""Root-finding (scalar and system) over SciPy — unified under
``kernel/computational`` (ADR 0022). Moved from ``kernel/numerics/
root_finding.py`` and ``root_system.py``; logic unchanged, only the
return type (now wrapping :class:`~oec.kernel.computational.diagnostics.
ComputationalDiagnostics`) differs.

Method selection is explicit, never silent (plan section 4.4): the caller
states ``method`` directly, or a documented default is applied based on
which inputs were given (a bracket vs. an initial guess) — see
:func:`select_default_method`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Literal

import numpy as np
import scipy.optimize
from pydantic import BaseModel, ConfigDict
from scipy.optimize import root

from oec.errors import NumericalDomainError
from oec.kernel.computational.diagnostics import ComputationalDiagnostics

BracketedMethod = Literal["brentq", "bisect"]
OpenMethod = Literal["secant", "newton"]

_BRACKETED_METHODS: dict[BracketedMethod, Callable[..., tuple[Any, Any]]] = {
    "brentq": scipy.optimize.brentq,
    "bisect": scipy.optimize.bisect,
}


class RootResult(BaseModel):
    """A scalar root-finding call's outcome: the root and how it was obtained."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    root: float
    diagnostics: ComputationalDiagnostics


class RootSystemResult(BaseModel):
    """A nonlinear-system root-finding call's outcome."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    x: list[float]
    diagnostics: ComputationalDiagnostics


def select_default_method(*, has_bracket: bool, has_initial_guess: bool) -> str:
    """The documented, explicit method-selection rule (plan section 4.4).

    A bracket takes precedence when both are given (brentq is preferred
    over bisection: same robustness guarantee, faster convergence). An
    initial guess alone selects the secant method — Newton's method
    requires a derivative; pass one explicitly via ``fprime`` (e.g. built
    with :func:`oec.kernel.computational.differentiation.differentiate`)
    to opt into ``method="newton"``.
    """
    if has_bracket:
        return "brentq"
    if has_initial_guess:
        return "secant"
    raise NumericalDomainError(
        "cannot select a root-finding method without a bracket [a, b] or an initial guess x0",
        details={"has_bracket": has_bracket, "has_initial_guess": has_initial_guess},
    )


def find_root_bracketed(
    f: Callable[[float], float],
    a: float,
    b: float,
    *,
    method: BracketedMethod = "brentq",
    xtol: float = 2e-12,
    rtol: float = 8.881784197001252e-16,
    max_iterations: int = 100,
) -> RootResult:
    """Find a root of ``f`` in ``[a, b]`` via Brent's method or bisection.

    Raises :class:`~oec.errors.NumericalDomainError` if ``f(a)`` and
    ``f(b)`` don't have opposite signs (no valid bracket) or ``method``
    isn't recognized -- both are malformed calls, not solver outcomes.
    Non-convergence within ``max_iterations`` is *not* raised; it comes
    back as ``diagnostics.converged is False``, per ADR 0007.
    """
    if method not in _BRACKETED_METHODS:
        raise NumericalDomainError(
            f"unknown bracketed root-finding method {method!r}",
            details={"method": method, "allowed": sorted(_BRACKETED_METHODS)},
        )

    solver = _BRACKETED_METHODS[method]
    try:
        root_value, info = solver(
            f, a, b, xtol=xtol, rtol=rtol, maxiter=max_iterations, full_output=True, disp=False
        )
    except ValueError as exc:
        raise NumericalDomainError(
            f"invalid bracket [{a}, {b}]: {exc}",
            details={"a": a, "b": b, "f_a": f(a), "f_b": f(b)},
        ) from exc

    return RootResult(
        root=float(root_value),
        diagnostics=ComputationalDiagnostics(
            method=method,
            backend="scipy",
            converged=bool(info.converged),
            iterations=int(info.iterations),
            function_calls=int(info.function_calls),
            residual=abs(f(float(root_value))),
        ),
    )


def find_root_from_guess(
    f: Callable[[float], float],
    x0: float,
    *,
    method: OpenMethod = "secant",
    fprime: Callable[[float], float] | None = None,
    tolerance: float = 1.48e-08,
    max_iterations: int = 50,
) -> RootResult:
    """Find a root of ``f`` starting from ``x0`` via the secant method or Newton's method.

    ``method="newton"`` requires ``fprime``; omitting it is a malformed
    call (:class:`~oec.errors.NumericalDomainError`), not silently
    downgraded to secant.
    """
    if method == "newton" and fprime is None:
        raise NumericalDomainError(
            "method='newton' requires fprime; omit it to use method='secant' instead",
            details={"method": method},
        )
    if method == "secant" and fprime is not None:
        raise NumericalDomainError(
            "method='secant' does not take fprime; pass method='newton' to use a derivative",
            details={"method": method},
        )

    root_value, info = scipy.optimize.newton(
        f,
        x0,
        fprime=fprime,
        tol=tolerance,
        maxiter=max_iterations,
        full_output=True,
        disp=False,
    )

    return RootResult(
        root=float(root_value),
        diagnostics=ComputationalDiagnostics(
            method=method,
            backend="scipy",
            converged=bool(info.converged),
            iterations=int(info.iterations),
            function_calls=int(info.function_calls),
            residual=abs(f(float(root_value))),
        ),
    )


def solve_root_system(
    fun: Callable[[Any], Any],
    x0: Sequence[float],
    *,
    method: str = "hybr",
    tol: float = 1.49012e-08,
) -> RootSystemResult:
    """Solve a nonlinear system ``f(x) = 0`` via SciPy's ``root``."""
    x0_arr = np.array(list(x0), dtype=float)

    def wrapped(x: Any) -> Any:
        return np.asarray(fun(x), dtype=float)

    sol = root(wrapped, x0_arr, method=method, tol=tol)  # type: ignore[call-overload]
    residual = np.asarray(fun(sol.x), dtype=float)

    return RootSystemResult(
        x=[float(v) for v in np.asarray(sol.x, dtype=float).tolist()],
        diagnostics=ComputationalDiagnostics(
            method=method,
            backend="scipy",
            converged=bool(sol.success),
            function_calls=int(getattr(sol, "nfev", 0) or 0),
            residual=float(np.linalg.norm(residual, ord=2)),
            message=str(sol.message),
        ),
    )
