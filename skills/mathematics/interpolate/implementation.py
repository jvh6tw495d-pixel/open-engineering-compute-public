"""mathematics.interpolate entrypoint.

Runs inside the sandboxed subprocess (ADR 0012) — imported only by
``oec.execution.runner``, never by the Skill Loader or the parent
process. Constructs a 1-D interpolant from discrete samples and
evaluates it at the requested query points; see ``skill.md``'s
"Official methodology" for why ``method`` is mandatory (no auto-select).

This method is closed-form construction + evaluation, not iterative —
``method.iterative: false`` in ``skill.yaml``, so ``diagnostics`` does
**not** report ``converged`` (ADR 0013: only iterative methods must).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    x = np.asarray(inputs["x"], dtype=float)
    y = np.asarray(inputs["y"], dtype=float)
    query_points = np.asarray(inputs["query_points"], dtype=float)
    method: str = inputs["method"]

    if method == "linear":
        # numpy.interp: simple, no SciPy interp1d deprecation path
        values = np.interp(query_points, x, y)
    elif method == "cubic_spline":
        spline = CubicSpline(x, y)
        values = spline(query_points)
    elif method == "pchip":
        interpolant = PchipInterpolator(x, y)
        values = interpolant(query_points)
    else:
        # Schema enum should have rejected this; fail loud if it didn't.
        raise ValueError(f"unsupported method: {method!r}")

    # JSON-serializable Python floats (numpy scalars are not json.dumps-safe).
    values_list = [float(v) for v in np.asarray(values, dtype=float).ravel()]

    return {
        "result": {"values": values_list},
        "diagnostics": {
            "method": method,
            "n_samples": int(x.size),
            "n_query": int(query_points.size),
        },
    }
