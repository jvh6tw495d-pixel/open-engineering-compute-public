"""Central dimensional normalization (ADR 0016).

Converts every input a skill's ``input.schema.json`` declares an
``x-oec-unit`` for (see :mod:`oec.kernel.units.schema`) into that
canonical unit, once, inside :class:`~oec.execution.service.ExecutionService`
-- so ``380 V`` and ``0.38 kV`` submitted for the same field are
indistinguishable by the time a skill's ``implementation.py`` runs.

:func:`apply_dimensional_normalization` is deliberately a **pure,
non-failing transform**, not a validator: `ExecutionService.execute()`
only calls it after every input validator -- including
:class:`~oec.validation.dimensions.DimensionalValidator`, which performs
the actual compatibility check -- has already reported no ``ERROR``
outcome. Compatibility is therefore already guaranteed by the time this
runs, so converting cannot itself fail; re-checking here would either
duplicate `DimensionalValidator`'s `ValidationOutcome` for the same
mismatch or require this function to also produce outcomes, which the
frozen `InputValidator`/`ResultValidator` protocols (the Sprint 03
"congelar interface de Validator" contract) don't allow for a plain
input-transform step.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.units.normalize import normalize
from oec.kernel.units.quantity import QuantityValue
from oec.kernel.units.schema import declared_units, is_quantity_dict
from oec.skills.loader.models import LoadedSkill


def apply_dimensional_normalization(skill: LoadedSkill, inputs: dict[str, Any]) -> dict[str, Any]:
    """Return ``inputs`` with every ``x-oec-unit``-declared field converted to that unit.

    Fields that aren't declared, or aren't QuantityValue-shaped, pass
    through unchanged. Assumes compatibility was already confirmed --
    see the module docstring.
    """
    properties = skill.input_schema.get("properties")
    if not isinstance(properties, dict):
        return inputs

    expected_units = declared_units(properties)
    if not expected_units:
        return inputs

    converted = dict(inputs)
    for field, expected_unit in expected_units.items():
        raw = inputs.get(field)
        if not is_quantity_dict(raw):
            continue
        quantity = QuantityValue(**raw)
        result = normalize(quantity, to_unit=expected_unit)
        converted[field] = result.normalized.model_dump(mode="json")

    return converted
