"""Golden + schema-runtime tests for uncertainty.propagate_linear 0.2.0."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")
_OUTPUT_SCHEMA = json.loads((_SKILL_DIR / "output.schema.json").read_text(encoding="utf-8"))
_validator = Draft202012Validator(_OUTPUT_SCHEMA)


def test_independent_sum_variance() -> None:
    out = implementation.execute(
        {
            "jacobian": [1.0, 1.0],
            "covariance": [[1.0, 0.0], [0.0, 1.0]],
        }
    )["result"]
    assert abs(out["variance"] - 2.0) < 1e-12
    assert abs(out["std"] - 2.0**0.5) < 1e-12
    assert "nominal_output" not in out
    _validator.validate(out)


def test_nominal_output_present_and_schema_valid() -> None:
    """Schema-runtime: nominal provided ⇒ nominal_output accepted by schema."""
    out = implementation.execute(
        {
            "jacobian": [1.0, 2.0],
            "covariance": [[1.0, 0.0], [0.0, 1.0]],
            "nominal": [3.0, 4.0],
        }
    )["result"]
    assert out["nominal"] == [3.0, 4.0]
    assert out["nominal_output"] == [pytest.approx(11.0)]
    # Must not raise Additional properties / type errors
    _validator.validate(out)


def test_nominal_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="nominal length"):
        implementation.execute(
            {
                "jacobian": [1.0, 1.0],
                "covariance": [[1.0, 0.0], [0.0, 1.0]],
                "nominal": [1.0],
            }
        )


def test_matrix_jacobian_nominal_output_schema() -> None:
    out = implementation.execute(
        {
            "jacobian": [[1.0, 0.0], [0.0, 2.0]],
            "covariance": [[1.0, 0.0], [0.0, 1.0]],
            "nominal": [1.0, 3.0],
        }
    )["result"]
    assert out["nominal_output"] == [pytest.approx(1.0), pytest.approx(6.0)]
    _validator.validate(out)
