"""Thin HiGHS adapter (Phase B/C).

Scientific merit: HiGHS / highspy. OEC only translates structured models
and maps solver status — it does not claim algorithmic ownership.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from oec.errors import OECError


class HighsNotAvailableError(OECError):
    """Raised when the optional ``highspy`` extra is not installed."""

    default_code = "highs_not_available"


class SolverStatus(StrEnum):
    OPTIMAL = "optimal"
    INFEASIBLE = "infeasible"
    UNBOUNDED = "unbounded"
    TIME_LIMIT = "time_limit"
    OTHER = "other"


@dataclass(frozen=True)
class LinearVariable:
    name: str
    lower: float | None = 0.0
    upper: float | None = None
    kind: Literal["continuous", "integer", "binary"] = "continuous"
    objective_coeff: float = 0.0


@dataclass(frozen=True)
class LinearConstraint:
    name: str
    coeffs: dict[str, float]
    sense: Literal["<=", ">=", "="]
    rhs: float


@dataclass
class LinearSolveResult:
    status: SolverStatus
    objective_value: float | None
    primal: dict[str, float] = field(default_factory=dict)
    dual: dict[str, float] = field(default_factory=dict)
    mip_gap: float | None = None
    mip_node_count: int | None = None
    message: str = ""
    raw_status: str = ""


def _require_highspy() -> Any:
    try:
        import highspy  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise HighsNotAvailableError(
            "HiGHS is not installed. Install with: uv sync --extra optimization "
            "(or pip install 'oec[optimization]')",
            details={"package": "highspy"},
        ) from exc
    return highspy


def solve_linear(
    *,
    variables: list[LinearVariable],
    constraints: list[LinearConstraint],
    sense: Literal["min", "max"] = "min",
    time_limit_seconds: float | None = None,
) -> LinearSolveResult:
    """Solve LP or MILP with HiGHS."""
    highspy = _require_highspy()
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    if time_limit_seconds is not None and time_limit_seconds > 0:
        h.setOptionValue("time_limit", float(time_limit_seconds))

    inf = float(highspy.kHighsInf)
    name_to_var: dict[str, Any] = {}
    for var in variables:
        if var.kind == "binary":
            v = h.addBinary()
        elif var.kind == "integer":
            lo = -inf if var.lower is None else float(var.lower)
            hi = inf if var.upper is None else float(var.upper)
            v = h.addIntegral(lb=lo, ub=hi)
        else:
            lo = -inf if var.lower is None else float(var.lower)
            hi = inf if var.upper is None else float(var.upper)
            v = h.addVariable(lb=lo, ub=hi)
        name_to_var[var.name] = v

    for cons in constraints:
        expr: Any = 0
        for vname, coeff in cons.coeffs.items():
            if vname not in name_to_var:
                raise OECError(
                    f"constraint {cons.name!r} references unknown variable {vname!r}",
                    code="ops_unknown_variable",
                    details={"constraint": cons.name, "variable": vname},
                )
            expr = expr + float(coeff) * name_to_var[vname]
        if cons.sense == "<=":
            h.addConstr(expr <= float(cons.rhs))
        elif cons.sense == ">=":
            h.addConstr(expr >= float(cons.rhs))
        else:
            h.addConstr(expr == float(cons.rhs))

    obj: Any = 0
    for var in variables:
        obj = obj + float(var.objective_coeff) * name_to_var[var.name]
    if sense == "min":
        h.minimize(obj)
    else:
        h.maximize(obj)

    model_status = h.getModelStatus()
    status_name = str(model_status).rsplit(".", maxsplit=1)[-1]
    mapped = _map_status(status_name)
    info = h.getInfo()
    values = list(h.allVariableValues())
    primal = {
        var.name: float(values[i]) if i < len(values) else 0.0 for i, var in enumerate(variables)
    }

    dual: dict[str, float] = {}
    try:
        row_duals = list(h.allConstrDuals())
        for i, cons in enumerate(constraints):
            if i < len(row_duals):
                dual[cons.name] = float(row_duals[i])
    except Exception:  # noqa: BLE001
        dual = {}

    mip_gap = getattr(info, "mip_gap", None)
    mip_nodes = getattr(info, "mip_node_count", None)
    obj_val = getattr(info, "objective_function_value", None)

    return LinearSolveResult(
        status=mapped,
        objective_value=None if obj_val is None else float(obj_val),
        primal=primal,
        dual=dual,
        mip_gap=None if mip_gap is None else float(mip_gap),
        mip_node_count=None if mip_nodes is None else int(mip_nodes),
        message=status_name,
        raw_status=status_name,
    )


def check_bound_conflicts(variables: list[LinearVariable]) -> list[str]:
    """Return human-readable issues for inverted variable bounds."""
    issues: list[str] = []
    for var in variables:
        if var.lower is not None and var.upper is not None and var.lower > var.upper:
            issues.append(
                f"variable {var.name!r}: lower bound {var.lower} > upper bound {var.upper}"
            )
    return issues


def _map_status(status_name: str) -> SolverStatus:
    name = status_name.lower()
    if "optimal" in name:
        return SolverStatus.OPTIMAL
    if "infeasible" in name:
        return SolverStatus.INFEASIBLE
    if "unbounded" in name:
        return SolverStatus.UNBOUNDED
    if "time" in name or "limit" in name:
        return SolverStatus.TIME_LIMIT
    return SolverStatus.OTHER
