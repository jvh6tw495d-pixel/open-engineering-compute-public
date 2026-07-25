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
