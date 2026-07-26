from __future__ import annotations

from typing import Any

from oec.kernel.linear.solve import solve_dense


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = solve_dense(inputs["A"], inputs["b"])
    diagnostics = {"converged": not out["singular"], "singular": out["singular"]}
    if out["singular"]:
        diagnostics["message"] = "matrix is singular or ill-conditioned for solve"
    return {"result": out, "diagnostics": diagnostics}
