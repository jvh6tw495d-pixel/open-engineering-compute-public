import math

import pytest
from pydantic import ValidationError

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
