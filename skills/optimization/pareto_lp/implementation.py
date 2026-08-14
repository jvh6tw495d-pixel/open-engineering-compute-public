"""optimization.pareto_lp entrypoint."""

from __future__ import annotations

from typing import Any

from oec.kernel.optimization.pareto import pareto_weighted_sum
from oec.ops.models import validate_ops


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    problem = validate_ops(inputs["ops"])
    if problem.problem_class != "lp":
        raise ValueError("optimization.pareto_lp requires ops.problem_class='lp'")
    out = pareto_weighted_sum(
        inputs["ops"],
        objective_a=dict(inputs["objective_a"]),
        objective_b=dict(inputs["objective_b"]),
        n_points=int(inputs.get("n_points", 11)),
    )
    return {
        "result": out,
        "diagnostics": {
            "n_nondominated": out["n_nondominated"],
            "n_solved_optimal": out["n_solved_optimal"],
            "converged": out["n_solved_optimal"] > 0,
            "backend": out["backend"],
        },
    }
