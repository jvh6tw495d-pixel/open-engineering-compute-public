"""Linear CVaR optimization (Rockafellar–Uryasev). Merit: HiGHS."""

from __future__ import annotations

from typing import Any

from oec.kernel.optimization.highs import (
    HighsNotAvailableError,
    LinearConstraint,
    LinearVariable,
    SolverStatus,
    solve_linear,
)


def cvar_lp(
    *,
    decision_vars: list[dict[str, Any]],
    loss_scenarios: list[dict[str, float]],
    alpha: float,
    sense: str = "min",
    structural_constraints: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Minimize (or report) CVaR_α of a linear loss over finite scenarios.

    Decision variables are continuous with optional bounds. Each scenario
    provides loss coefficients ``loss_s(x) = c_s · x``. Auxiliary variables:
    ``t`` (VaR level) and ``u_s >= loss_s - t``.

    Objective (min):
        ``t + 1/((1-α) S) * Σ u_s``

    Parameters
    ----------
    decision_vars:
        ``[{name, lower?, upper?}, ...]``
    loss_scenarios:
        List of coeff maps, one per scenario.
    alpha:
        Confidence level in ``(0, 1)`` (e.g. 0.95).
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0, 1)")
    if not decision_vars:
        raise ValueError("decision_vars must be non-empty")
    if not loss_scenarios:
        raise ValueError("loss_scenarios must be non-empty")
    if sense not in {"min", "max"}:
        raise ValueError("sense must be min or max")
    # CVaR formulation is naturally a minimization of tail loss.
    if sense == "max":
        raise ValueError("cvar_lp v0 supports sense='min' only (minimize CVaR of loss)")

    n_scen = len(loss_scenarios)
    inv_tail = 1.0 / ((1.0 - alpha) * n_scen)

    variables: list[LinearVariable] = []
    for v in decision_vars:
        variables.append(
            LinearVariable(
                name=str(v["name"]),
                lower=None if v.get("lower") is None else float(v["lower"]),
                upper=None if v.get("upper") is None else float(v["upper"]),
                kind="continuous",
                objective_coeff=0.0,
            )
        )
    # t free
    variables.append(
        LinearVariable(
            name="__cvar_t", lower=None, upper=None, kind="continuous", objective_coeff=1.0
        )
    )
    for s in range(n_scen):
        variables.append(
            LinearVariable(
                name=f"__cvar_u_{s}",
                lower=0.0,
                upper=None,
                kind="continuous",
                objective_coeff=inv_tail,
            )
        )

    constraints: list[LinearConstraint] = []
    # Structural constraints on decision vars only
    for i, cons in enumerate(structural_constraints or []):
        coeffs = {str(k): float(v) for k, v in dict(cons["coeffs"]).items()}
        constraints.append(
            LinearConstraint(
                name=str(cons.get("name", f"struct_{i}")),
                coeffs=coeffs,
                sense=str(cons["sense"]),  # type: ignore[arg-type]
                rhs=float(cons["rhs"]),
            )
        )
    # u_s >= loss_s - t  <=>  loss_s - t - u_s <= 0
    for s, scen in enumerate(loss_scenarios):
        coeffs = {str(k): float(v) for k, v in scen.items()}
        coeffs["__cvar_t"] = -1.0
        coeffs[f"__cvar_u_{s}"] = -1.0
        constraints.append(
            LinearConstraint(
                name=f"tail_{s}",
                coeffs=coeffs,
                sense="<=",
                rhs=0.0,
            )
        )

    try:
        solved = solve_linear(variables=variables, constraints=constraints, sense="min")
    except HighsNotAvailableError as exc:
        return {
            "solver_status": "other",
            "cvar": None,
            "var_level": None,
            "primal": {},
            "decision": {},
            "tail_excesses": [],
            "alpha": float(alpha),
            "n_scenarios": n_scen,
            "feasibility_issues": [exc.message],
            "backend": "highs",
            "method": "rockafellar_uryasev",
            "converged": False,
        }

    primal = solved.primal
    decision = {v["name"]: float(primal.get(str(v["name"]), 0.0)) for v in decision_vars}
    t_val = float(primal.get("__cvar_t", 0.0))
    us = [float(primal.get(f"__cvar_u_{s}", 0.0)) for s in range(n_scen)]
    cvar_val = t_val + inv_tail * sum(us) if solved.status is SolverStatus.OPTIMAL else None

    return {
        "solver_status": solved.status.value,
        "cvar": cvar_val,
        "var_level": t_val if solved.status is SolverStatus.OPTIMAL else None,
        "primal": primal,
        "decision": decision,
        "tail_excesses": us,
        "alpha": float(alpha),
        "n_scenarios": n_scen,
        "feasibility_issues": []
        if solved.status is SolverStatus.OPTIMAL
        else [f"HiGHS status: {solved.status.value}"],
        "backend": "highs",
        "method": "rockafellar_uryasev",
        "converged": solved.status is SolverStatus.OPTIMAL,
    }
