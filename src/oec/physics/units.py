"""Unit-boundary helpers for physics-library consumers.

All conversion is delegated to the kernel's single shared Pint registry via
``QuantityValue``.  This module deliberately owns no registry and performs no
skill-input normalization; ``x-oec-unit`` normalization remains an
``ExecutionService`` responsibility (ADR 0016).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import pint

from oec.kernel.units.quantity import QuantityValue
from oec.kernel.units.registry import ureg
from oec.physics.errors import PhysicsError
from oec.physics.result import ConservationCheck
from oec.physics.types import PhysicsDomain


@dataclass(frozen=True)
class ToleranceDefaults:
    """Default tolerance and canonical residual unit for one domain."""

    atol: float
    rtol: float
    residual_unit: str


CANONICAL_UNITS: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {
        "P1": MappingProxyType({"power": "W", "voltage": "V", "current": "A", "resistance": "ohm"}),
        "P2": MappingProxyType(
            {
                "temperature": "K",
                "thermal_conductivity": "W / (m * K)",
                "heat": "J",
                "heat_rate": "W",
            }
        ),
        "P3": MappingProxyType({"length": "m", "velocity": "m / s", "force": "N", "energy": "J"}),
        "P4": MappingProxyType({"pressure": "Pa", "density": "kg / m ** 3", "velocity": "m / s"}),
        "P5": MappingProxyType({"stress": "Pa", "density": "kg / m ** 3", "elastic_modulus": "Pa"}),
    }
)

TOLERANCE_DEFAULTS: Mapping[PhysicsDomain, ToleranceDefaults] = MappingProxyType(
    {
        PhysicsDomain.ELECTRICAL: ToleranceDefaults(1e-6, 1e-9, "W"),
        PhysicsDomain.THERMAL: ToleranceDefaults(1e-6, 1e-9, "W"),
        PhysicsDomain.MECHANICS: ToleranceDefaults(1e-9, 1e-9, "N"),
        PhysicsDomain.FLUIDS: ToleranceDefaults(1e-6, 1e-9, "Pa"),
        PhysicsDomain.MATERIALS: ToleranceDefaults(1e-3, 1e-9, "Pa"),
    }
)


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


def evaluate_dimensional_residual(
    residual: QuantityValue,
    *,
    domain: PhysicsDomain,
    scale: QuantityValue,
    atol: QuantityValue | None = None,
    rtol: float | None = None,
) -> ConservationCheck:
    """Convert tolerance inputs to one unit and apply the conservation policy."""
    from oec.physics.conservation import evaluate_residual

    defaults = TOLERANCE_DEFAULTS[domain]
    canonical_residual = as_canonical(residual, defaults.residual_unit)
    canonical_scale = as_canonical(scale, defaults.residual_unit)
    canonical_atol = (
        QuantityValue(value=defaults.atol, unit=defaults.residual_unit)
        if atol is None
        else as_canonical(atol, defaults.residual_unit)
    )
    return evaluate_residual(
        canonical_residual.value,
        atol=canonical_atol.value,
        rtol=defaults.rtol if rtol is None else rtol,
        scale=canonical_scale.value,
        unit=defaults.residual_unit,
    )


__all__ = [
    "CANONICAL_UNITS",
    "TOLERANCE_DEFAULTS",
    "PhysicsUnitError",
    "ToleranceDefaults",
    "as_canonical",
    "evaluate_dimensional_residual",
    "require_compatible",
]
