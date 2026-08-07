import math

import pytest
from pydantic import ValidationError

from oec.kernel.units.constants import CATALOG_VERSION, constants, get_constant
from oec.kernel.units.operations import QuantityOperationError
from oec.kernel.units.quantity import QuantityValue


def test_valid_quantity_constructs() -> None:
    q = QuantityValue(value=75, unit="kW")
    assert q.value == 75.0
    assert q.unit == "kW"


def test_quantity_is_frozen() -> None:
    q = QuantityValue(value=75, unit="kW")
    with pytest.raises(ValidationError):
        q.value = 100  # type: ignore[misc]


@pytest.mark.parametrize("unit", ["", "notaunit", "kW extra garbage"])
def test_invalid_unit_is_rejected(unit: str) -> None:
    with pytest.raises(ValidationError):
        QuantityValue(value=1.0, unit=unit)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_value_is_rejected(value: float) -> None:
    with pytest.raises(ValidationError):
        QuantityValue(value=value, unit="V")


def test_negative_value_is_allowed() -> None:
    """QuantityValue makes no sign assumption -- some quantities (voltage
    drop, reactive power, temperature in Celsius) can legitimately be
    negative. Sign constraints belong to a skill's own physical-layer
    validation (plan section 12.4), not to the generic value object."""
    q = QuantityValue(value=-10.0, unit="V")
    assert q.value == -10.0


def test_serializes_to_the_plan_public_shape() -> None:
    q = QuantityValue(value=75, unit="kW")
    assert q.model_dump(mode="json") == {"value": 75.0, "unit": "kW"}


def test_public_dimension_api_does_not_expose_a_pint_object() -> None:
    quantity = QuantityValue(value=10.0, unit="m/s")
    assert quantity.dimension == "[length]^1*[time]^-1"
    assert isinstance(quantity.dimension, str)


def test_public_conversion_returns_quantity_value_shape() -> None:
    converted = QuantityValue(value=1.5, unit="kW").convert_to("W")
    assert converted.model_dump(mode="json") == {"value": 1500.0, "unit": "W"}


def test_compatible_quantity_arithmetic_preserves_a_json_safe_result() -> None:
    total = QuantityValue(value=1.0, unit="kW").add(QuantityValue(value=500.0, unit="W"))
    assert total.model_dump(mode="json") == {"value": 1.5, "unit": "kW"}


@pytest.mark.parametrize(
    "operation",
    [
        lambda left, right: left.add(right),
        lambda left, right: left.subtract(right),
    ],
)
def test_incompatible_quantity_arithmetic_raises_typed_error(operation: object) -> None:
    left = QuantityValue(value=1.0, unit="V")
    right = QuantityValue(value=1.0, unit="W")
    with pytest.raises(QuantityOperationError) as exc_info:
        operation(left, right)  # type: ignore[operator]
    assert exc_info.value.code == "quantity_operation_invalid"


def test_offset_temperature_converts_but_does_not_allow_generic_arithmetic() -> None:
    freezing = QuantityValue(value=0.0, unit="degC")
    assert freezing.convert_to("kelvin") == QuantityValue(value=273.15, unit="kelvin")
    with pytest.raises(QuantityOperationError):
        freezing.add(QuantityValue(value=1.0, unit="degC"))


def test_dimensionless_operation_is_rejected_with_a_typed_error() -> None:
    with pytest.raises(QuantityOperationError) as exc_info:
        QuantityValue(value=1.0, unit="V").divide(QuantityValue(value=1.0, unit="V"))
    assert exc_info.value.code == "quantity_operation_invalid"


def test_constant_catalogue_embeds_versioned_provenance() -> None:
    speed_of_light = get_constant("speed_of_light_in_vacuum")
    assert speed_of_light.quantity == QuantityValue(value=299_792_458.0, unit="m/s")
    assert speed_of_light.source_version == CATALOG_VERSION
    assert speed_of_light.exact is True
    assert "planck_constant" in constants()
