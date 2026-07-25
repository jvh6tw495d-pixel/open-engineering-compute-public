"""Dimensional validation and normalization of physical quantities.

Per ADR 0003, converting a quantity to a canonical unit must never lose
the unit it was originally submitted in — a future ``ExecutionResult``'s
provenance needs it. :func:`normalize` returns both the original and the
converted quantity together so callers never have to choose between
normalizing and preserving provenance.
"""

from __future__ import annotations

import pint
from pydantic import BaseModel, ConfigDict

from oec.errors import UnitError
from oec.kernel.units.quantity import QuantityValue
from oec.kernel.units.registry import ureg
from oec.kernel.units.serialization import to_pint


class NormalizedQuantity(BaseModel):
    """A quantity alongside its normalized form, for provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    original: QuantityValue
    normalized: QuantityValue


def is_compatible(unit_a: str, unit_b: str) -> bool:
    """Whether a quantity in ``unit_a`` can be converted to ``unit_b``."""
    try:
        ureg.Quantity(1.0, unit_a).to(unit_b)
    except pint.errors.PintError:
        return False
    return True


def normalize(quantity: QuantityValue, *, to_unit: str) -> NormalizedQuantity:
    """Convert ``quantity`` to ``to_unit``, keeping the original for provenance.

    Raises :class:`~oec.errors.UnitError` if ``quantity.unit`` and
    ``to_unit`` are dimensionally incompatible (or if ``to_unit`` itself
    is not a unit Pint recognizes).
    """
    try:
        converted = to_pint(quantity).to(to_unit)
    except pint.errors.PintError as exc:
        raise UnitError(
            f"cannot convert {quantity.unit!r} to {to_unit!r}: {exc}",
            details={"from_unit": quantity.unit, "to_unit": to_unit},
        ) from exc

    normalized = QuantityValue(value=float(converted.magnitude), unit=to_unit)
    return NormalizedQuantity(original=quantity, normalized=normalized)
