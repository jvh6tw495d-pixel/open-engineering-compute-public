"""Reusable physical-limit checks for skill-specific validation (plan section 12.4).

Like :mod:`oec.validation.mathematical`, these are pure helpers called from a
skill's own ``validation.py``, not pipeline-wired validator classes. They
cover physical constraints that JSON Schema cannot express cleanly —
notably absolute-zero bounds that depend on the temperature unit.
"""

from __future__ import annotations

import pint

from oec.kernel.units.registry import ureg
from oec.validation.base import Severity, ValidationOutcome

LAYER = "physical"


def require_positive(field: str, value: float) -> ValidationOutcome:
    """Require ``value`` to be strictly greater than zero."""
    if value <= 0.0:
        return ValidationOutcome(
            layer=LAYER,
            severity=Severity.ERROR,
            messages=[f"field {field!r} must be positive, got {value}"],
            details={"field": field, "value": value},
        )
    return ValidationOutcome(layer=LAYER, severity=Severity.OK)


def require_probability(field: str, value: float) -> ValidationOutcome:
    """Require ``value`` in ``[0, 1]`` (power factor, efficiency, probability)."""
    if value < 0.0 or value > 1.0:
        return ValidationOutcome(
            layer=LAYER,
            severity=Severity.ERROR,
            messages=[f"field {field!r} must be a probability in [0, 1], got {value}"],
            details={"field": field, "value": value},
        )
    return ValidationOutcome(layer=LAYER, severity=Severity.OK)


def require_above_absolute_zero(field: str, value: float, unit: str) -> ValidationOutcome:
    """Require a temperature strictly above absolute zero, unit-aware via Pint.

    Converts ``value unit`` to kelvin rather than hardcoding per-unit limits,
    so ``0 K``, ``-273.15 degC``, and ``-459.67 degF`` are all rejected.
    """
    try:
        kelvin = ureg.Quantity(value, unit).to("kelvin")
    except pint.errors.PintError as exc:
        return ValidationOutcome(
            layer=LAYER,
            severity=Severity.ERROR,
            messages=[f"field {field!r}: cannot interpret temperature {value} {unit}: {exc}"],
            details={"field": field, "value": value, "unit": unit},
        )

    kelvin_value = float(kelvin.magnitude)
    if kelvin_value <= 0.0:
        return ValidationOutcome(
            layer=LAYER,
            severity=Severity.ERROR,
            messages=[
                f"field {field!r}: temperature {value} {unit} "
                f"({kelvin_value} K) is not above absolute zero"
            ],
            details={
                "field": field,
                "value": value,
                "unit": unit,
                "kelvin": kelvin_value,
            },
        )
    return ValidationOutcome(layer=LAYER, severity=Severity.OK)
