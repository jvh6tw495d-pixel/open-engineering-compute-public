import pytest

from oec.errors import UnitError
from oec.kernel.units.normalize import dimension_of, is_compatible, normalize
from oec.kernel.units.quantity import QuantityValue


def test_equivalent_quantities_in_different_units_normalize_to_the_same_value() -> None:
    """The core Sprint 02 acceptance criterion: entradas equivalentes em
    unidades diferentes convergem ao mesmo valor normalizado."""
    from_volts = normalize(QuantityValue(value=380.0, unit="V"), to_unit="V")
    from_kilovolts = normalize(QuantityValue(value=0.38, unit="kV"), to_unit="V")
    assert from_volts.normalized.value == from_kilovolts.normalized.value == 380.0
    assert from_volts.normalized.unit == from_kilovolts.normalized.unit == "V"


def test_normalize_preserves_the_original_quantity_for_provenance() -> None:
    original = QuantityValue(value=0.38, unit="kV")
    result = normalize(original, to_unit="V")
    assert result.original == original
    assert result.original.unit == "kV"
    assert result.normalized.unit == "V"


def test_normalize_is_a_no_op_value_change_when_already_in_the_target_unit() -> None:
    result = normalize(QuantityValue(value=75.0, unit="kW"), to_unit="kW")
    assert result.normalized.value == 75.0


def test_incompatible_units_raise_unit_error() -> None:
    """acceptance criterion: unidades incompatíveis falham."""
    with pytest.raises(UnitError) as exc_info:
        normalize(QuantityValue(value=380.0, unit="V"), to_unit="W")
    assert exc_info.value.code == "unit_incompatible"
    assert exc_info.value.details == {"from_unit": "V", "to_unit": "W"}


def test_normalize_to_an_unknown_unit_raises_unit_error() -> None:
    with pytest.raises(UnitError):
        normalize(QuantityValue(value=1.0, unit="V"), to_unit="notaunit")


@pytest.mark.parametrize(
    ("unit_a", "unit_b", "expected"),
    [
        ("V", "kV", True),
        ("kW", "W", True),
        ("A", "mA", True),
        ("V", "W", False),
        ("Hz", "V", False),
    ],
)
def test_is_compatible(unit_a: str, unit_b: str, expected: bool) -> None:
    assert is_compatible(unit_a, unit_b) is expected


@pytest.mark.parametrize(
    ("value", "source_unit", "target_unit", "expected"),
    [
        (0.0, "degC", "kelvin", 273.15),
        (32.0, "degF", "degC", 0.0),
        (273.15, "kelvin", "degC", 0.0),
    ],
)
def test_normalize_handles_offset_temperature_units(
    value: float, source_unit: str, target_unit: str, expected: float
) -> None:
    result = normalize(QuantityValue(value=value, unit=source_unit), to_unit=target_unit)
    assert result.normalized.value == pytest.approx(expected)
    assert result.normalized.unit == target_unit


def test_dimension_of_unknown_unit_raises_typed_error() -> None:
    with pytest.raises(UnitError) as exc_info:
        dimension_of("not-a-unit")
    assert exc_info.value.code == "unit_incompatible"
