import math

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.kernel.units.normalize import normalize
from oec.kernel.units.quantity import QuantityValue

# Small, well-behaved multiplicative unit family (SI power/electrical
# prefixes) -- avoids offset units (e.g. degC) where round-tripping
# through a different unit is a genuinely different, non-trivial claim.
_COMPATIBLE_UNIT_PAIRS = st.sampled_from(
    [
        ("V", "kV"),
        ("V", "mV"),
        ("W", "kW"),
        ("W", "mW"),
        ("A", "mA"),
        ("Hz", "kHz"),
        ("ohm", "kohm"),
    ]
)
_FINITE_VALUES = st.floats(
    min_value=-1e9, max_value=1e9, allow_nan=False, allow_infinity=False
).filter(lambda v: abs(v) > 1e-9 or v == 0.0)
_TEMPERATURE_VALUES = st.floats(
    min_value=-250.0, max_value=10_000.0, allow_nan=False, allow_infinity=False
)


@settings(deadline=None)
@given(unit_pair=_COMPATIBLE_UNIT_PAIRS, value=_FINITE_VALUES)
def test_normalizing_and_converting_back_recovers_the_original_value(
    unit_pair: tuple[str, str], value: float
) -> None:
    unit_a, unit_b = unit_pair
    original = QuantityValue(value=value, unit=unit_a)

    to_b = normalize(original, to_unit=unit_b)
    back_to_a = normalize(to_b.normalized, to_unit=unit_a)

    assert math.isclose(back_to_a.normalized.value, value, rel_tol=1e-9, abs_tol=1e-9)


@settings(deadline=None)
@given(unit_pair=_COMPATIBLE_UNIT_PAIRS, value=_FINITE_VALUES)
def test_normalizing_twice_to_the_same_unit_is_idempotent(
    unit_pair: tuple[str, str], value: float
) -> None:
    unit_a, unit_b = unit_pair
    original = QuantityValue(value=value, unit=unit_a)

    once = normalize(original, to_unit=unit_b)
    twice = normalize(once.normalized, to_unit=unit_b)

    assert math.isclose(once.normalized.value, twice.normalized.value, rel_tol=1e-9)


@settings(deadline=None)
@given(value=_TEMPERATURE_VALUES)
def test_offset_temperature_round_trip_is_stable(value: float) -> None:
    original = QuantityValue(value=value, unit="degC")
    kelvin = normalize(original, to_unit="kelvin")
    recovered = normalize(kelvin.normalized, to_unit="degC")

    assert math.isclose(recovered.normalized.value, value, rel_tol=1e-12, abs_tol=1e-10)
