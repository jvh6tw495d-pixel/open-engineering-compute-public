"""Applied Mathematics Specialist v0.1 - formulate skill inputs, run OEC, narrate.

Harness only: LLMs use ``prompts/``; numerical answers always come from
:class:`oec.sdk.Engine`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from agents.common import SkillSpecialist

from oec.kernel.numerics.expressions import compile_expression


@dataclass
class MathRequestReport:
    """Structured result for narrow natural-language math requests."""

    agent: str
    request: str
    interpreted_as: str
    normalized_expression: str
    bounds: list[float]
    variable: str = "x"
    offset_hours: float | None = None
    min_execution: dict[str, Any] | None = None
    max_execution: dict[str, Any] | None = None
    narrative: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "request": self.request,
            "interpreted_as": self.interpreted_as,
            "normalized_expression": self.normalized_expression,
            "bounds": self.bounds,
            "variable": self.variable,
            "offset_hours": self.offset_hours,
            "min_execution": self.min_execution,
            "max_execution": self.max_execution,
            "narrative": self.narrative,
            "notes": self.notes,
        }


class AppliedMathematicsSpecialist(SkillSpecialist):
    """Maps math demos to mathematics/linear/statistics/numerical skills."""

    name = "applied_mathematics_specialist"
    demos = {
        "sqrt2": (
            "mathematics.solve_root",
            {"expression": "x**2 - 2", "bracket": [0, 2]},
        ),
        "solve_root": (
            "mathematics.solve_root",
            {"expression": "x**2 - 2", "bracket": [0, 2]},
        ),
        "integrate_x2": (
            "mathematics.integrate",
            {"expression": "x**2", "bounds": [0.0, 1.0]},
        ),
        "linear_identity": (
            "linear.solve_system",
            {"A": [[2.0, 0.0], [0.0, 2.0]], "b": [2.0, 4.0]},
        ),
        "matrix_properties": (
            "linear.matrix_properties",
            {"A": [[2.0, 0.0], [0.0, 3.0]]},
        ),
        "describe": (
            "statistics.describe",
            {"values": [1.0, 2.0, 3.0, 4.0]},
        ),
        "monte_carlo": (
            "statistics.monte_carlo",
            {
                "expression": "x**2",
                "n_samples": 5000,
                "low": 0.0,
                "high": 1.0,
                "seed": 42,
            },
        ),
        "ode_decay": (
            "numerical.ode_ivp",
            {
                "state_names": ["y"],
                "dydt_expressions": ["-y"],
                "t_span": [0.0, 1.0],
                "y0": [1.0],
                "t_eval": [0.0, 0.5, 1.0],
            },
        ),
    }

    def run_request(self, request: str) -> MathRequestReport:
        parsed = _parse_scalar_extrema_request(request)
        expression = parsed["expression"]
        bounds = parsed["bounds"]

        min_report = self.run_skill(
            "mathematics.optimize_scalar",
            {"expression": expression, "bounds": bounds, "method": "bounded"},
        )
        max_report = self.run_skill(
            "mathematics.optimize_scalar",
            {"expression": f"-({expression})", "bounds": bounds, "method": "bounded"},
        )

        assert min_report.execution is not None
        assert max_report.execution is not None

        evaluator = compile_expression(expression)
        x_min = float(min_report.execution.result["x"])
        x_max = float(max_report.execution.result["x"])
        value_min = float(min_report.execution.result["fun"])
        value_max = -float(max_report.execution.result["fun"])

        report = MathRequestReport(
            agent=self.name,
            request=request,
            interpreted_as="scalar_extrema_on_closed_interval",
            normalized_expression=expression,
            bounds=[float(bounds[0]), float(bounds[1])],
            variable=parsed["variable"],
            offset_hours=parsed["offset_hours"],
            min_execution=min_report.execution.model_dump(mode="json"),
            max_execution=max_report.execution.model_dump(mode="json"),
            notes=list(parsed["notes"]),
        )
        report.narrative = _build_extrema_narrative(
            variable=parsed["variable"],
            bounds=(float(bounds[0]), float(bounds[1])),
            x_min=x_min,
            x_max=x_max,
            value_min=value_min,
            value_max=value_max,
            offset_hours=parsed["offset_hours"],
            original_expr=parsed["original_expression"],
            normalized_expr=expression,
            endpoint_values=(
                (float(bounds[0]), float(evaluator(float(bounds[0])))),
                (float(bounds[1]), float(evaluator(float(bounds[1])))),
            ),
        )
        return report


def _parse_scalar_extrema_request(request: str) -> dict[str, Any]:
    assignment = re.search(
        r"([A-Za-z]\w*)\s*\(\s*([A-Za-z])\s*\)\s*=\s*(.+?)(?=,?\s+(?:onde|where|com|for)\b|,?\s+(?:km/h|kmh)\b|[\.\n\r]|$)",
        request,
        flags=re.IGNORECASE,
    )
    if assignment is None:
        raise ValueError(
            "Applied Mathematics Specialist could not extract a function assignment like f(x)=..."
        )

    variable = assignment.group(2)
    original_expression = assignment.group(3).strip().rstrip(".,;")
    normalized_expression = _normalize_expression(original_expression, variable)

    bounds = _extract_bounds(request)
    offset_hours = _infer_hour_offset(request, variable, bounds)
    if offset_hours is not None:
        bounds = [float(bounds[0] - offset_hours), float(bounds[1] - offset_hours)]

    return {
        "variable": variable,
        "original_expression": original_expression,
        "expression": normalized_expression,
        "bounds": [float(bounds[0]), float(bounds[1])],
        "offset_hours": offset_hours,
        "notes": [f"clock_interval_shifted_by_{offset_hours}"] if offset_hours is not None else [],
    }


def _normalize_expression(expression: str, variable: str) -> str:
    normalized = re.sub(r"(?<=\d),(?=\d)", ".", expression)
    normalized = normalized.replace("^", "**").replace("−", "-")
    if variable != "x":
        normalized = re.sub(rf"\b{re.escape(variable)}\b", "x", normalized)
    normalized = re.sub(r"(?<=\d)\s+(?=x\b|\()", "*", normalized)
    normalized = re.sub(r"(?<=x)\s+(?=\d|\()", "*", normalized)
    normalized = re.sub(r"(?<=\))\s+(?=x\b|\d|\()", "*", normalized)
    return normalized.strip()


def _extract_bounds(request: str) -> list[float]:
    bracket = re.search(r"\[\s*(-?\d+(?:[.,]\d+)?)\s*,\s*(-?\d+(?:[.,]\d+)?)\s*\]", request)
    if bracket is not None:
        return [_to_float(bracket.group(1)), _to_float(bracket.group(2))]

    between = re.search(
        r"\b(?:entre|between|from)\s+(-?\d+(?:[.,]\d+)?)\s+(?:e|and|to)\s+(-?\d+(?:[.,]\d+)?)",
        request,
        flags=re.IGNORECASE,
    )
    if between is not None:
        return [_to_float(between.group(1)), _to_float(between.group(2))]

    raise ValueError(
        "Applied Mathematics Specialist could not extract a closed interval "
        "like [a, b] or 'entre a e b'."
    )


def _infer_hour_offset(request: str, variable: str, bounds: list[float]) -> float | None:
    if variable.lower() != "t":
        return None

    lower_request = request.lower()
    noon_phrasing = (
        "após o meio-dia" in lower_request
        or "apos o meio-dia" in lower_request
        or "after noon" in lower_request
    )
    if noon_phrasing and bounds[0] >= 12 and bounds[1] >= 12:
        return 12.0
    return None


def _to_float(raw: str) -> float:
    return float(raw.replace(",", "."))


def _build_extrema_narrative(
    *,
    variable: str,
    bounds: tuple[float, float],
    x_min: float,
    x_max: float,
    value_min: float,
    value_max: float,
    offset_hours: float | None,
    original_expr: str,
    normalized_expr: str,
    endpoint_values: tuple[tuple[float, float], tuple[float, float]],
) -> str:
    lo, hi = bounds
    left_x, left_value = endpoint_values[0]
    right_x, right_value = endpoint_values[1]

    def render_point(x: float) -> str:
        if offset_hours is None:
            return f"{variable}={x:.6g}"
        return f"{variable}={x:.6g} ({x + offset_hours:.6g}h)"

    lines = [
        "Applied Mathematics Specialist handled a natural-language scalar extrema request.",
        f"Original expression: {original_expr}",
        f"Normalized expression for OEC scalar skills: {normalized_expr}",
        f"Closed interval used: [{lo:.6g}, {hi:.6g}]",
        f"Minimum found: {render_point(x_min)} with value {value_min:.6g}",
        f"Maximum found: {render_point(x_max)} with value {value_max:.6g}",
        f"Endpoint check: {variable}={left_x:.6g} -> {left_value:.6g}; "
        f"{variable}={right_x:.6g} -> {right_value:.6g}",
        "Numbers come from OEC mathematics.optimize_scalar runs; endpoint values "
        "are direct evaluations of the same normalized expression.",
    ]
    return "\n".join(lines)
