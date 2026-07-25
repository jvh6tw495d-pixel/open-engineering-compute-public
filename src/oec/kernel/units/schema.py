"""Shared helpers for interpreting the ``x-oec-unit`` JSON Schema extension.

``x-oec-unit`` is an OEC-specific extension (not part of the JSON Schema
standard): when an ``input.schema.json`` property declares
``"x-oec-unit": "V"``, that field's submitted value is expected to be a
:class:`~oec.kernel.units.quantity.QuantityValue`-shaped dict
(``{"value": ..., "unit": ...}``) convertible to volts.

Both :class:`~oec.validation.dimensions.DimensionalValidator` (checks
compatibility, produces a `ValidationOutcome`) and
:mod:`oec.execution.normalization` (performs the actual conversion, once
compatibility is already confirmed) need to answer the same two
questions -- "which fields does this schema declare a canonical unit
for" and "does this value look like a quantity at all" -- so the logic
lives here once rather than in each of those two modules independently.
"""

from __future__ import annotations

from typing import Any, TypeGuard

_QUANTITY_KEYS = frozenset({"value", "unit"})


def declared_units(properties: dict[str, Any]) -> dict[str, str]:
    """Map each field declaring ``x-oec-unit`` to its expected canonical unit."""
    return {
        field: field_schema["x-oec-unit"]
        for field, field_schema in properties.items()
        if isinstance(field_schema, dict) and isinstance(field_schema.get("x-oec-unit"), str)
    }


def is_quantity_dict(value: object) -> TypeGuard[dict[str, Any]]:
    """Whether ``value`` is shaped like a QuantityValue dict (exactly ``{value, unit}``)."""
    return isinstance(value, dict) and set(value.keys()) == _QUANTITY_KEYS
