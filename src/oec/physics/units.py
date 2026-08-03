"""Unit-boundary helpers for physics-library consumers.

All conversion is delegated to the kernel's single shared Pint registry via
``QuantityValue``.  This module deliberately owns no registry and performs no
skill-input normalization; ``x-oec-unit`` normalization remains an
``ExecutionService`` responsibility (ADR 0016).
"""

from __future__ import annotations

import pint

from oec.kernel.units.quantity import QuantityValue
from oec.kernel.units.registry import ureg
from oec.physics.errors import PhysicsError


class PhysicsUnitError(PhysicsError):
    """Raised when a physics quantity is incompatible with its canonical unit."""

    default_code = "physics_unit_incompatible"


def require_compatible(quantity: QuantityValue, canonical_unit: str) -> QuantityValue:
    """Return ``quantity`` if compatible with ``canonical_unit``, else fail closed."""
    try:
        compatible = ureg.Quantity(quantity.value, quantity.unit).is_compatible_with(
            ureg.Quantity(1.0, canonical_unit)
        )
    except pint.errors.PintError as exc:
        raise PhysicsUnitError(
            f"cannot validate unit {quantity.unit!r} against {canonical_unit!r}: {exc}",
            details={"actual_unit": quantity.unit, "canonical_unit": canonical_unit},
        ) from exc

    if not compatible:
        raise PhysicsUnitError(
            f"unit {quantity.unit!r} is incompatible with canonical unit {canonical_unit!r}",
            details={
                "actual_unit": quantity.unit,
                "actual_dimension": quantity.dimension,
                "canonical_unit": canonical_unit,
            },
        )
    return quantity


def as_canonical(quantity: QuantityValue, canonical_unit: str) -> QuantityValue:
    """Convert a compatible quantity to the requested canonical unit."""
    require_compatible(quantity, canonical_unit)
    try:
        return quantity.convert_to(canonical_unit)
    except pint.errors.PintError as exc:
        raise PhysicsUnitError(
            f"cannot convert unit {quantity.unit!r} to {canonical_unit!r}: {exc}",
            details={"actual_unit": quantity.unit, "canonical_unit": canonical_unit},
        ) from exc


__all__ = ["PhysicsUnitError", "as_canonical", "require_compatible"]
