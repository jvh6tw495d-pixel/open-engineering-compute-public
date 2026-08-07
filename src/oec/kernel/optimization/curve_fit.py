"""Nonlinear least-squares curve fitting wrappers over SciPy (plan
section 14.x: ``math.curve_fit``).

Method selection is explicit, never silent (plan section 4.4): no
``bounds`` selects Levenberg-Marquardt (``lm``, SciPy's classic
unconstrained least-squares solver — it does not support bounds at
all); ``bounds`` selects Trust Region Reflective (``trf``). ``dogbox``
is available as an explicit alternative to ``trf`` for bounded
problems. Mixing ``bounds`` with ``method="lm"`` is rejected, not
silently switched to ``trf``.

Diagnostics follow the same
:class:`~oec.kernel.optimization.diagnostics.OptimizationDiagnostics`
shape every optimization skill reports through: ``residuals``/
``covariance`` are this method's own signature fields (nothing else in
the kernel sets them); ``optimality``/``constraint_violation``/
``feasible`` don't apply to curve fitting and are always ``None``,
never fabricated.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Literal

import numpy as np
import scipy.optimize
from pydantic import BaseModel, ConfigDict

from oec.errors import NumericalDomainError
from oec.kernel.optimization.diagnostics import OptimizationDiagnostics

CurveFitMethod = Literal["lm", "trf", "dogbox"]

_METHODS: frozenset[str] = frozenset({"lm", "trf", "dogbox"})


class CurveFitResult(BaseModel):
    """A curve-fit call's outcome: the fitted parameters and how they were found."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    params: list[float]
    diagnostics: OptimizationDiagnostics


def select_default_method(*, has_bounds: bool) -> CurveFitMethod:
    """The documented, explicit method-selection rule (plan section 4.4).

    Bounds select ``trf`` (Trust Region Reflective — the only one of the
    three methods, besides ``dogbox``, that supports bounds at all). No
    bounds select ``lm`` (Levenberg-Marquardt), SciPy's classic
    unconstrained least-squares default. ``dogbox`` remains available
    but only on explicit request.
    """
    return "trf" if has_bounds else "lm"


def fit_curve(
    model: Callable[[Sequence[float]], float],
    xdata: Sequence[float],
    ydata: Sequence[float],
    p0: Sequence[float],
    *,
    bounds: tuple[Sequence[float], Sequence[float]] | None = None,
    method: CurveFitMethod | None = None,
    max_iterations: int | None = None,
) -> CurveFitResult:
    """Fit ``model(x; *params)`` to ``(xdata, ydata)`` by nonlinear least squares.

    ``model`` takes one combined argument vector ``[x, *params]`` (the
    shape :func:`~oec.kernel.numerics.expressions.compile_expression_vector`
    produces), not SciPy's own ``f(x, *params)`` convention — this
    function adapts internally.

    Raises :class:`~oec.errors.NumericalDomainError` for a malformed
    call: an unrecognized ``method``, ``bounds`` combined with
    ``method="lm"``, mismatched ``xdata``/``ydata`` lengths, or fewer
    data points than free parameters (a least-squares fit is
    underdetermined otherwise). Non-convergence is *not* raised as an
    exception from this function — SciPy's own ``curve_fit`` raises
    ``RuntimeError`` internally when it fails to converge, which is
    caught here and turned into ``diagnostics.converged = False`` (a
    valid diagnostic outcome, per ADR 0007), with the exception message
    in ``diagnostics.message``. In that failure case, ``params``/
    ``residuals``/``covariance`` reflect the initial guess ``p0``, not a
    solver iterate — SciPy's ``RuntimeError`` path exposes no partial
    progress to fall back on.
    """
    resolved_method = method or select_default_method(has_bounds=bounds is not None)
    if resolved_method not in _METHODS:
        raise NumericalDomainError(
            f"unknown curve fit method {resolved_method!r}",
            details={"method": resolved_method, "allowed": sorted(_METHODS)},
        )
    if resolved_method == "lm" and bounds is not None:
        raise NumericalDomainError(
            "method='lm' does not support 'bounds'; use method='trf' or 'dogbox' instead",
            details={"method": resolved_method},
        )
    if len(xdata) != len(ydata):
        raise NumericalDomainError(
            f"'xdata' has {len(xdata)} entries but 'ydata' has {len(ydata)}",
            details={"n_xdata": len(xdata), "n_ydata": len(ydata)},
        )
    if len(xdata) < len(p0):
        raise NumericalDomainError(
            f"{len(xdata)} data point(s) is not enough to fit {len(p0)} parameter(s)",
            details={"n_data": len(xdata), "n_params": len(p0)},
        )

    def _vectorized_model(x: np.ndarray, *params: float) -> np.ndarray:
        return np.array([model([xi, *params]) for xi in np.atleast_1d(x)], dtype=float)

    kwargs: dict[str, Any] = {"p0": list(p0), "method": resolved_method, "full_output": True}
    if bounds is not None:
        kwargs["bounds"] = bounds
    if max_iterations is not None:
        kwargs["max_nfev" if resolved_method != "lm" else "maxfev"] = max_iterations

    try:
        popt, pcov, infodict, mesg, _ier = scipy.optimize.curve_fit(
            _vectorized_model,
            np.asarray(xdata, dtype=float),
            np.asarray(ydata, dtype=float),
            **kwargs,
        )
        converged = True
        message = str(mesg)
        n_function_evaluations = int(infodict["nfev"])
    except RuntimeError as exc:
        converged = False
        message = str(exc)
        popt = np.asarray(p0, dtype=float)
        pcov = np.full((len(p0), len(p0)), float("nan"))
        n_function_evaluations = 0
    except ValueError as exc:
        raise NumericalDomainError(
            f"invalid curve fit call: {exc}", details={"method": resolved_method}
        ) from exc

    params = [float(v) for v in np.atleast_1d(popt)]
    residuals = [float(ydata[i] - model([xdata[i], *params])) for i in range(len(xdata))]
    covariance = [[float(v) for v in row] for row in np.atleast_2d(pcov)]

    return CurveFitResult(
        params=params,
        diagnostics=OptimizationDiagnostics(
            method=resolved_method,
            converged=converged,
            message=message,
            # curve_fit's full_output infodict carries no separate iteration
            # count (unlike minimize/minimize_scalar's OptimizeResult.nit) --
            # n_iterations mirrors n_function_evaluations rather than
            # fabricating a number SciPy never reports here.
            n_iterations=n_function_evaluations,
            n_function_evaluations=n_function_evaluations,
            residuals=residuals,
            covariance=covariance,
        ),
    )
