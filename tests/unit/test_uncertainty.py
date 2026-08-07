import pytest
from pydantic import ValidationError

from oec.kernel.uncertainty import UncertainQuantity, Uncertainty
from oec.kernel.units.quantity import QuantityValue


def test_relative_uncertainty_is_json_safe_and_explicit() -> None:
    uncertainty = Uncertainty(
        kind="relative", value=0.02, confidence_level=0.95, source="sensor spec"
    )
    assert uncertainty.model_dump(mode="json") == {
        "kind": "relative",
        "value": 0.02,
        "unit": None,
        "confidence_level": 0.95,
        "source": "sensor spec",
    }


def test_absolute_uncertainty_must_match_quantity_dimension() -> None:
    measured = UncertainQuantity(
        quantity=QuantityValue(value=10.0, unit="V"),
        uncertainty=Uncertainty(kind="absolute", value=50.0, unit="mV"),
    )
    assert measured.uncertainty.unit == "mV"

    with pytest.raises(ValidationError, match="must match the quantity dimension"):
        UncertainQuantity(
            quantity=QuantityValue(value=10.0, unit="V"),
            uncertainty=Uncertainty(kind="absolute", value=1.0, unit="W"),
        )


@pytest.mark.parametrize("interval_unit", ["K", "delta_degC", "delta_degF"])
def test_celsius_accepts_multiplicative_temperature_uncertainty(interval_unit: str) -> None:
    measured = UncertainQuantity(
        quantity=QuantityValue(value=20.0, unit="degC"),
        uncertainty=Uncertainty(kind="absolute", value=0.5, unit=interval_unit),
    )
    assert measured.uncertainty.unit == interval_unit


@pytest.mark.parametrize("affine_unit", ["degC", "degF"])
def test_absolute_uncertainty_rejects_affine_temperature_unit(affine_unit: str) -> None:
    with pytest.raises(ValidationError, match="multiplicative interval unit"):
        Uncertainty(kind="absolute", value=0.5, unit=affine_unit)


def test_relative_uncertainty_is_a_fraction_and_may_exceed_one() -> None:
    uncertainty = Uncertainty(kind="relative", value=1.25)
    assert uncertainty.value == 1.25


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "absolute", "value": 1.0},
        {"kind": "relative", "value": 0.1, "unit": "%"},
        {"kind": "absolute", "value": -1.0, "unit": "V"},
        {"kind": "relative", "value": 0.1, "confidence_level": 1.1},
    ],
)
def test_invalid_uncertainty_representation_is_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Uncertainty.model_validate(payload)
