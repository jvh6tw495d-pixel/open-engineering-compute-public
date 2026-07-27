"""``QuantityValue``: the public, JSON-friendly representation of a physical quantity.

Per ADR 0003, physical quantities are never bare floats. The public shape
is::

    {"value": 75, "unit": "kW"}

Dimensionless numbers (counts, ratios, power factor) are explicitly out
of scope for this model — they stay plain numbers in a skill's schema,
per ADR 0003's consequences. A skill that needs a dimensionless physical
ratio should say so in its own input schema, not smuggle it through
``QuantityValue`` with an empty or fake unit.
"""

from __future__ import annotations

import math

import pint
from pydantic import BaseModel, ConfigDict, field_validator

from oec.kernel.units.registry import ureg


class QuantityValue(BaseModel):
    """A physical quantity: a numeric value paired with an explicit unit."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float
    unit: str

    @field_validator("value")
    @classmethod
    def _validate_value(cls, value: float) -> float:
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"quantity value must be finite, got {value!r}")
        return value

    @field_validator("unit")
    @classmethod
    def _validate_unit(cls, value: str) -> str:
        if not value:
            raise ValueError("unit must not be empty; use a plain number for a dimensionless value")
        try:
            ureg.parse_units(value)
        except pint.UndefinedUnitError as exc:
            raise ValueError(f"unknown unit {value!r}: {exc}") from exc
        return value

    @property
    def dimension(self) -> str:
        """Return the quantity's canonical dimensionality string.

        The return value is deliberately a string (for example
        ``"[mass] * [length] / [time] ** 2"``), rather than Pint's
        ``UnitsContainer``.  This keeps Pint an implementation detail of the
        kernel while providing a stable, JSON-friendly public API.
        """
        from oec.kernel.units.normalize import dimension_of

        return dimension_of(self.unit)

    def convert_to(self, unit: str) -> QuantityValue:
        """Return this quantity expressed in ``unit``.

        The method returns only the converted value.  Call
        :func:`oec.kernel.units.normalize.normalize` when the original value
        must be retained for execution provenance.
        """
        from oec.kernel.units.normalize import normalize

        return normalize(self, to_unit=unit).normalized

    def is_compatible_with(self, other: QuantityValue) -> bool:
        """Whether ``other`` has the same physical dimensionality."""
        from oec.kernel.units.normalize import is_compatible

        return is_compatible(self.unit, other.unit)

    def add(self, other: QuantityValue) -> QuantityValue:
        """Add a dimensionally compatible quantity in this quantity's unit."""
        from oec.kernel.units.operations import add

        return add(self, other)

    def subtract(self, other: QuantityValue) -> QuantityValue:
        """Subtract a dimensionally compatible quantity in this quantity's unit."""
        from oec.kernel.units.operations import subtract

        return subtract(self, other)

    def multiply(self, other: QuantityValue) -> QuantityValue:
        """Multiply two quantities, producing a derived-unit quantity."""
        from oec.kernel.units.operations import multiply

        return multiply(self, other)

    def divide(self, other: QuantityValue) -> QuantityValue:
        """Divide two quantities, producing a derived-unit quantity."""
        from oec.kernel.units.operations import divide

        return divide(self, other)
