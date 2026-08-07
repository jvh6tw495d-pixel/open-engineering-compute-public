"""Convert validated OPS problems into HiGHS linear models."""

from __future__ import annotations

from oec.kernel.optimization.highs import LinearConstraint, LinearVariable
from oec.ops.models import OPSProblem


def ops_to_linear_parts(
    problem: OPSProblem,
) -> tuple[list[LinearVariable], list[LinearConstraint], str]:
    """Return (variables, constraints, sense) for :func:`solve_linear`."""
    obj_coeffs = dict(problem.objective.coeffs)
    variables: list[LinearVariable] = []
    for var in problem.variables:
        coeff = float(obj_coeffs.get(var.name, var.objective_coeff))
        # objective.coeffs wins over per-variable objective_coeff
        if var.name in obj_coeffs:
            coeff = float(obj_coeffs[var.name])
        elif var.objective_coeff:
            coeff = float(var.objective_coeff)
        else:
            coeff = float(obj_coeffs.get(var.name, 0.0))

        lower = var.lower
        upper = var.upper
        if var.kind == "binary":
            lower = 0.0 if lower is None else lower
            upper = 1.0 if upper is None else upper

        variables.append(
            LinearVariable(
                name=var.name,
                lower=lower,
                upper=upper,
                kind=var.kind,
                objective_coeff=coeff,
            )
        )

    constraints = [
        LinearConstraint(
            name=c.name,
            coeffs={k: float(v) for k, v in c.coeffs.items()},
            sense=c.sense,
            rhs=float(c.rhs),
        )
        for c in problem.constraints
    ]
    return variables, constraints, problem.sense
