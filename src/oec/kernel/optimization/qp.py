"""Quadratic programming via SciPy SLSQP (S23–S24 v0).

Merit: SciPy. Form: minimize 0.5 x^T Q x + c^T x  s.t. bounds and linear Ax ? b.
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import scipy.optimize


def solve_qp(
    q: list[list[float]],
    c: list[float],
    *,
    x0: list[float] | None = None,
    bounds: list[list[float | None]] | None = None,
    a_ub: list[list[float]] | None = None,
    b_ub: list[float] | None = None,
    a_eq: list[list[float]] | None = None,
    b_eq: list[float] | None = None,
    sense: Literal["min", "max"] = "min",
) -> dict[str, Any]:
    q_arr: Any = np.array(q, dtype=float)
    c_arr: Any = np.array(c, dtype=float)
    if q_arr.ndim != 2 or q_arr.shape[0] != q_arr.shape[1]:
        raise ValueError("Q must be square")
    n = int(q_arr.shape[0])
    if c_arr.shape != (n,):
        raise ValueError("c length must match Q dimension")

    sign = 1.0 if sense == "min" else -1.0

    def fun(x: Any) -> float:
        return float(sign * (0.5 * x @ q_arr @ x + c_arr @ x))

    def jac(x: Any) -> Any:
        # gradient of 0.5 x'Qx + c'x is 0.5(Q+Q')x + c
        g = 0.5 * (q_arr + q_arr.T) @ x + c_arr
        return sign * g

    x_start = np.zeros(n) if x0 is None else np.array(x0, dtype=float)
    if x_start.shape != (n,):
        raise ValueError("x0 length must match dimension")

    scipy_bounds = None
    if bounds is not None:
        if len(bounds) != n:
            raise ValueError("bounds length must match dimension")
        scipy_bounds = []
        for pair in bounds:
            if len(pair) != 2:
                raise ValueError("each bound must be [lower, upper]")
            lo, hi = pair[0], pair[1]
            scipy_bounds.append(
                (
                    None if lo is None else float(lo),
                    None if hi is None else float(hi),
                )
            )

    constraints: list[dict[str, Any]] = []
    if a_ub is not None:
        a_ub_arr: Any = np.array(a_ub, dtype=float)
        b_ub_arr: Any = np.array(b_ub if b_ub is not None else [], dtype=float)
        if a_ub_arr.size:
            if a_ub_arr.ndim != 2 or a_ub_arr.shape[1] != n:
                raise ValueError("A_ub must be (m, n)")
            if b_ub_arr.shape != (a_ub_arr.shape[0],):
                raise ValueError("b_ub length must match A_ub rows")
            for i in range(a_ub_arr.shape[0]):
                row = a_ub_arr[i]
                rhs = float(b_ub_arr[i])
                constraints.append(
                    {
                        "type": "ineq",
                        "fun": lambda x, r=row, rhs=rhs: float(rhs - r @ x),
                    }
                )
    if a_eq is not None:
        a_eq_arr: Any = np.array(a_eq, dtype=float)
        b_eq_arr: Any = np.array(b_eq if b_eq is not None else [], dtype=float)
        if a_eq_arr.size:
            if a_eq_arr.ndim != 2 or a_eq_arr.shape[1] != n:
                raise ValueError("A_eq must be (m, n)")
            if b_eq_arr.shape != (a_eq_arr.shape[0],):
                raise ValueError("b_eq length must match A_eq rows")
            for i in range(a_eq_arr.shape[0]):
                row = a_eq_arr[i]
                rhs = float(b_eq_arr[i])
                constraints.append(
                    {
                        "type": "eq",
                        "fun": lambda x, r=row, rhs=rhs: float(r @ x - rhs),
                    }
                )

    res = scipy.optimize.minimize(  # type: ignore[call-overload]
        fun,
        x_start,
        method="SLSQP",
        jac=jac,
        bounds=scipy_bounds,
        constraints=constraints,
    )
    x_star = [float(v) for v in res.x.tolist()]
    # Report true quadratic value (not signed for max)
    x_np: Any = np.array(x_star, dtype=float)
    true_obj = float(0.5 * x_np @ q_arr @ x_np + c_arr @ x_np)
    return {
        "x": x_star,
        "objective_value": true_obj,
        "sense": sense,
        "success": bool(res.success),
        "message": str(res.message),
        "nit": int(res.nit) if res.nit is not None else None,
        "backend": "scipy.optimize.minimize/SLSQP",
    }
