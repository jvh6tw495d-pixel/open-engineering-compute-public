import pytest

from oec.errors import UnitError
from oec.kernel.units.normalize import is_compatible, normalize
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
