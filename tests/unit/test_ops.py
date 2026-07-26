"""OPS v0.1 validation tests (Phase C)."""

import pytest

from oec.errors import OECValidationError
from oec.ops.models import validate_ops
from oec.ops.schema import OPS_SCHEMA_VERSION


def _lp_doc(**overrides):
    doc = {
        "ops_version": OPS_SCHEMA_VERSION,
        "problem_class": "lp",
        "sense": "min",
        "variables": [
            {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
            {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
        ],
        "constraints": [
            {"name": "c1", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1},
        ],
        "objective": {"coeffs": {"x": 1, "y": 1}},
    }
    doc.update(overrides)
    return doc


def test_valid_lp_ops() -> None:
    problem = validate_ops(_lp_doc())
    assert problem.problem_class == "lp"
    assert len(problem.variables) == 2


def test_lp_rejects_integer_vars() -> None:
    with pytest.raises(OECValidationError):
        validate_ops(
            _lp_doc(
                variables=[{"name": "x", "kind": "binary"}],
                constraints=[{"name": "c", "coeffs": {"x": 1}, "sense": "<=", "rhs": 1}],
                objective={"coeffs": {"x": 1}},
            )
        )


def test_milp_requires_integer() -> None:
    with pytest.raises(OECValidationError):
        validate_ops(_lp_doc(problem_class="milp"))


def test_unknown_variable_in_constraint() -> None:
    with pytest.raises(OECValidationError):
        validate_ops(
            _lp_doc(
                constraints=[
                    {"name": "bad", "coeffs": {"z": 1}, "sense": "<=", "rhs": 1},
                ]
            )
        )


def test_inverted_bounds() -> None:
    with pytest.raises(OECValidationError):
        validate_ops(
            _lp_doc(
                variables=[
                    {"name": "x", "kind": "continuous", "lower": 5, "upper": 1},
                ],
                constraints=[],
                objective={"coeffs": {"x": 1}},
            )
        )
