"""Conversions between the public :class:`QuantityValue` and Pint's internal
:class:`pint.Quantity`, always going through the shared registry."""

from __future__ import annotations

import pint

from oec.kernel.units.quantity import QuantityValue
from oec.kernel.units.registry import ureg


def to_pint(quantity: QuantityValue) -> pint.Quantity:  # type: ignore[type-arg]
    """Build a Pint quantity from a public :class:`QuantityValue`."""
    return ureg.Quantity(quantity.value, quantity.unit)


def from_pint(quantity: pint.Quantity) -> QuantityValue:  # type: ignore[type-arg]
    """Build a public :class:`QuantityValue` from a Pint quantity.

    Renders the unit in Pint's short/abbreviated form (e.g. ``kW``, not
    ``kilowatt``) to match the style used in ``skill.md`` worked examples
    and the plan's own ``{"value": 75, "unit": "kW"}`` convention.
    """
    return QuantityValue(value=float(quantity.magnitude), unit=format(quantity.units, "~"))
