"""1-D interpolation — unified under ``kernel/computational`` (ADR 0022).
Moved out of ``skills/mathematics/interpolate/implementation.py``; same
three methods, same numpy/scipy calls, no behavior change.

Closed-form construction + evaluation, not iterative:
``diagnostics.converged`` is always ``None`` (ADR 0013).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict
from scipy.interpolate import CubicSpline, PchipInterpolator

from oec.errors import NumericalDomainError
from oec.kernel.computational.diagnostics import ComputationalDiagnostics

InterpolationMethod = Literal["linear", "cubic_spline", "pchip"]

_BACKEND_BY_METHOD: dict[str, str] = {
    "linear": "numpy",
    "cubic_spline": "scipy",
    "pchip": "scipy",
}


class InterpolationResult(BaseModel):
    """Interpolated values at the requested query points."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    values: list[float]
    diagnostics: ComputationalDiagnostics


def interpolate(
    x: Sequence[float],
    y: Sequence[float],
    query_points: Sequence[float],
    *,
    method: InterpolationMethod,
) -> InterpolationResult:
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    query_arr = np.asarray(query_points, dtype=float)

    if method == "linear":
        # numpy.interp: simple, no SciPy interp1d deprecation path
        values = np.interp(query_arr, x_arr, y_arr)
    elif method == "cubic_spline":
        values = CubicSpline(x_arr, y_arr)(query_arr)
    elif method == "pchip":
        values = PchipInterpolator(x_arr, y_arr)(query_arr)
    else:
        # Schema enum should have rejected this; fail loud if it didn't.
        raise NumericalDomainError(
            f"unsupported interpolation method {method!r}", details={"method": method}
        )

    values_list = [float(v) for v in np.asarray(values, dtype=float).ravel()]

    return InterpolationResult(
        values=values_list,
        diagnostics=ComputationalDiagnostics(
            method=method,
            backend=_BACKEND_BY_METHOD[method],
            converged=None,
        ),
    )
