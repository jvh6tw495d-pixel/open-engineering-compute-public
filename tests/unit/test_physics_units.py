"""Dimensional unit and conservation-tolerance matrix for Wave 2."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from oec.kernel.units import QuantityValue
from oec.modeling.ir import QuantityLiteral
from oec.physics.conservation import evaluate_residual
from oec.physics.dimensions import dimension_of, infer_dimension
from oec.physics.types import PhysicsDomain
from oec.physics.units import (
    CANONICAL_UNITS,
    TOLERANCE_DEFAULTS,
    PhysicsUnitError,
    as_canonical,
    evaluate_dimensional_residual,
    require_compatible,
)
from oec.validation.base import Severity
from oec.validation.physical import require_above_absolute_zero


@pytest.mark.parametrize(
    ("quantity", "canonical_unit", "expected"),
    [
        (QuantityValue(value=1.5, unit="kW"), "W", 1500.0),  # P1
        (QuantityValue(value=25.0, unit="degC"), "K", 298.15),  # P2
        (QuantityValue(value=36.0, unit="km / h"), "m / s", 10.0),  # P3
        (QuantityValue(value=1.0, unit="bar"), "Pa", 100_000.0),  # P4
    ],
)
def test_p1_to_p4_characteristic_units_convert_to_canonical(
    quantity: QuantityValue, canonical_unit: str, expected: float
) -> None:
    assert require_compatible(quantity, canonical_unit) is quantity
    converted = as_canonical(quantity, canonical_unit)
    assert converted.unit == canonical_unit
    assert converted.value == pytest.approx(expected)


def test_temperature_reuses_physical_absolute_zero_validation() -> None:
    assert require_above_absolute_zero("temperature", 25.0, "degC").severity is Severity.OK
    assert require_above_absolute_zero("temperature", -273.15, "degC").severity is Severity.ERROR


def test_voltage_is_not_mechanical_stress_even_though_both_are_called_tension() -> None:
    with pytest.raises(PhysicsUnitError) as raised:
        require_compatible(QuantityValue(value=230.0, unit="V"), "Pa")

    error = raised.value.to_dict()
    assert error["code"] == "physics_unit_incompatible"
    assert error["details"]["actual_unit"] == "V"
    assert error["details"]["canonical_unit"] == "Pa"


def test_unknown_target_unit_fails_closed_as_structured_error() -> None:
    with pytest.raises(PhysicsUnitError, match="cannot validate unit") as raised:
        require_compatible(QuantityValue(value=1.0, unit="W"), "not_a_unit")
    assert raised.value.details == {"actual_unit": "W", "canonical_unit": "not_a_unit"}


def test_expr_dimension_facade_delegates_to_modeling_dimension_inference() -> None:
    literal = QuantityLiteral(value=QuantityValue(value=2.0, unit="MPa"))
    assert infer_dimension(literal, {}) == dimension_of("Pa")


def test_canonical_table_covers_all_foundation_slices_and_named_units() -> None:
    assert set(CANONICAL_UNITS) == {"P1", "P2", "P3", "P4", "P5"}
    units = {unit for quantities in CANONICAL_UNITS.values() for unit in quantities.values()}
    assert {"W", "V", "A", "ohm", "K", "W / (m * K)", "m", "m / s"} <= units
    assert {"Pa", "kg / m ** 3", "J", "N"} <= units
    assert CANONICAL_UNITS["P5"]["stress"] == "Pa"


@pytest.mark.parametrize(
    ("domain", "residual", "scale", "atol", "rtol", "expected_balanced"),
    [
        (
            PhysicsDomain.ELECTRICAL,
            QuantityValue(value=0.001, unit="kW"),
            QuantityValue(value=1.0, unit="MW"),
            QuantityValue(value=0.5, unit="W"),
            1e-6,
            True,
        ),
        (
            PhysicsDomain.THERMAL,
            QuantityValue(value=2.0, unit="W"),
            QuantityValue(value=0.5, unit="kW"),
            QuantityValue(value=1.0, unit="mW"),
            1e-3,
            False,
        ),
        (
            PhysicsDomain.MECHANICS,
            QuantityValue(value=1.0, unit="mN"),
            QuantityValue(value=1.0, unit="kN"),
            QuantityValue(value=1.0, unit="uN"),
            1e-6,
            True,
        ),
        (
            PhysicsDomain.FLUIDS,
            QuantityValue(value=1.1, unit="kPa"),
            QuantityValue(value=1.0, unit="MPa"),
            QuantityValue(value=50.0, unit="Pa"),
            1e-3,
            False,
        ),
    ],
)
def test_tolerance_matrix_converts_distinct_units_before_mocked_formula(
    domain: PhysicsDomain,
    residual: QuantityValue,
    scale: QuantityValue,
    atol: QuantityValue,
    rtol: float,
    expected_balanced: bool,
) -> None:
    with patch("oec.physics.conservation.evaluate_residual", wraps=evaluate_residual) as mocked:
        check = evaluate_dimensional_residual(
            residual, domain=domain, scale=scale, atol=atol, rtol=rtol
        )

    assert check.balanced is expected_balanced
    assert check.unit == TOLERANCE_DEFAULTS[domain].residual_unit
    mocked.assert_called_once_with(
        check.residual,
        atol=check.atol,
        rtol=check.rtol,
        scale=check.scale,
        unit=check.unit,
    )
    assert check.balanced is (abs(check.residual) <= check.atol + check.rtol * check.scale)


def test_domain_defaults_are_used_and_audited() -> None:
    check = evaluate_dimensional_residual(
        QuantityValue(value=0.5, unit="mPa"),
        domain=PhysicsDomain.MATERIALS,
        scale=QuantityValue(value=2.0, unit="MPa"),
    )
    defaults = TOLERANCE_DEFAULTS[PhysicsDomain.MATERIALS]
    assert check.atol == defaults.atol
    assert check.rtol == defaults.rtol
    assert check.unit == defaults.residual_unit
    assert check.balanced


def test_incompatible_residual_unit_never_reaches_conservation_formula() -> None:
    with (
        patch("oec.physics.conservation.evaluate_residual") as mocked,
        pytest.raises(PhysicsUnitError),
    ):
        evaluate_dimensional_residual(
            QuantityValue(value=1.0, unit="A"),
            domain=PhysicsDomain.ELECTRICAL,
            scale=QuantityValue(value=1.0, unit="W"),
        )
    mocked.assert_not_called()
