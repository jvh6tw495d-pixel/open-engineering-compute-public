"""Scalar root-finding wrappers over SciPy (plan section 14.1: ``math.solve_root``).

Method selection is explicit, never silent (plan section 4.4): the
caller states ``method`` directly, or a documented default is applied
based on which inputs were given (a bracket vs. an initial guess) — see
:func:`select_default_method`. No function here decides "which SciPy
call looks convenient" on its own.

Diagnostics are always returned in the same shape
(:class:`RootFindingDiagnostics`), regardless of method, so
``compute_status`` (ADR 0007) and ``ExecutionService`` (ADR 0013) can
treat every method the same way: read ``converged``, done.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

import scipy.optimize
from pydantic import BaseModel, ConfigDict

from oec.errors import NumericalDomainError

BracketedMethod = Literal["brentq", "bisect"]
OpenMethod = Literal["secant", "newton"]

_BRACKETED_METHODS: dict[BracketedMethod, Callable[..., tuple[Any, Any]]] = {
    "brentq": scipy.optimize.brentq,
    "bisect": scipy.optimize.bisect,
}


class RootFindingDiagnostics(BaseModel):
    """Solver diagnostics in the shape ``compute_status`` expects (ADR 0007/0013)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    method: str
    converged: bool
    iterations: int
    function_calls: int
    residual: float


class RootFindingResult(BaseModel):
    """A root-finding call's outcome: the root and how it was obtained."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    root: float
    diagnostics: RootFindingDiagnostics


def select_default_method(*, has_bracket: bool, has_initial_guess: bool) -> str:
    """The documented, explicit method-selection rule (plan section 4.4).

    A bracket takes precedence when both are given (brentq is preferred
    over bisection: same robustness guarantee, faster convergence). An
    initial guess alone selects the secant method — Newton's method
    requires a derivative, which this MVP skill does not accept as
    input (no expression-differentiation support yet; see
    ``docs/sprints/`` for the scope decision).
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
) -> RootFindingResult:
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
        root, info = solver(
            f, a, b, xtol=xtol, rtol=rtol, maxiter=max_iterations, full_output=True, disp=False
        )
    except ValueError as exc:
        raise NumericalDomainError(
            f"invalid bracket [{a}, {b}]: {exc}",
            details={"a": a, "b": b, "f_a": f(a), "f_b": f(b)},
        ) from exc

    return RootFindingResult(
        root=float(root),
        diagnostics=RootFindingDiagnostics(
            method=method,
            converged=bool(info.converged),
            iterations=int(info.iterations),
            function_calls=int(info.function_calls),
            residual=abs(f(float(root))),
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
) -> RootFindingResult:
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

    root, info = scipy.optimize.newton(
        f,
        x0,
        fprime=fprime,
        tol=tolerance,
        maxiter=max_iterations,
        full_output=True,
        disp=False,
    )

    return RootFindingResult(
        root=float(root),
        diagnostics=RootFindingDiagnostics(
            method=method,
            converged=bool(info.converged),
            iterations=int(info.iterations),
            function_calls=int(info.function_calls),
            residual=abs(f(float(root))),
        ),
    )
