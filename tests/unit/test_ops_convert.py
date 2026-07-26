"""Unit tests for OPS → linear parts conversion (coverage F5)."""

from __future__ import annotations

from oec.ops.convert import ops_to_linear_parts
from oec.ops.models import validate_ops
from oec.ops.schema import OPS_SCHEMA_VERSION


def test_objective_coeffs_win_over_variable_objective_coeff() -> None:
    problem = validate_ops(
        {
            "ops_version": OPS_SCHEMA_VERSION,
            "problem_class": "lp",
            "sense": "min",
            "variables": [
                {
                    "name": "x",
                    "kind": "continuous",
                    "lower": 0,
                    "upper": 1,
                    "objective_coeff": 9.0,
                },
            ],
            "constraints": [],
            "objective": {"coeffs": {"x": 2.0}},
        }
    )
    variables, constraints, sense = ops_to_linear_parts(problem)
    assert sense == "min"
    assert constraints == []
    assert variables[0].objective_coeff == 2.0


def test_per_variable_objective_coeff_when_missing_from_objective() -> None:
    problem = validate_ops(
        {
            "ops_version": OPS_SCHEMA_VERSION,
            "problem_class": "lp",
            "sense": "max",
            "variables": [
                {
                    "name": "x",
                    "kind": "continuous",
                    "lower": 0,
                    "upper": 5,
                    "objective_coeff": 3.5,
                },
            ],
            "constraints": [],
            "objective": {"coeffs": {}},
        }
    )
    variables, _, sense = ops_to_linear_parts(problem)
    assert sense == "max"
    assert variables[0].objective_coeff == 3.5


def test_binary_default_bounds() -> None:
    problem = validate_ops(
        {
            "ops_version": OPS_SCHEMA_VERSION,
            "problem_class": "milp",
            "sense": "max",
            "variables": [{"name": "b", "kind": "binary"}],
            "constraints": [],
            "objective": {"coeffs": {"b": 1}},
        }
    )
    variables, _, _ = ops_to_linear_parts(problem)
    assert variables[0].lower == 0.0
    assert variables[0].upper == 1.0
    assert variables[0].kind == "binary"


def test_constraints_converted() -> None:
    problem = validate_ops(
        {
            "ops_version": OPS_SCHEMA_VERSION,
            "problem_class": "lp",
            "sense": "min",
            "variables": [
                {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
                {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
            ],
            "constraints": [
                {"name": "cover", "coeffs": {"x": 1.0, "y": 2.0}, "sense": ">=", "rhs": 1.5},
            ],
            "objective": {"coeffs": {"x": 1, "y": 1}},
        }
    )
    _variables, constraints, _sense = ops_to_linear_parts(problem)
    assert len(constraints) == 1
    assert constraints[0].name == "cover"
    assert constraints[0].coeffs == {"x": 1.0, "y": 2.0}
    assert constraints[0].sense == ">="
    assert constraints[0].rhs == 1.5
