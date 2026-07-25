from oec.kernel.units.quantity import QuantityValue
from oec.kernel.units.serialization import from_pint, to_pint


def test_to_pint_round_trips_through_from_pint() -> None:
    original = QuantityValue(value=75.0, unit="kW")
    pint_quantity = to_pint(original)
    restored = from_pint(pint_quantity)
    assert restored.value == 75.0
    assert restored.unit == "kW"


def test_from_pint_uses_short_unit_form() -> None:
    original = QuantityValue(value=1.0, unit="kilowatt")
    restored = from_pint(to_pint(original))
    assert restored.unit == "kW"


def test_to_pint_preserves_magnitude() -> None:
    quantity = to_pint(QuantityValue(value=380.0, unit="V"))
    assert quantity.magnitude == 380.0
    assert str(quantity.units) == "volt"
