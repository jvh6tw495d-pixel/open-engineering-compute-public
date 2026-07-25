"""Dimensional validation of physical quantities in skill inputs (plan section 12.2).

``x-oec-unit`` is an OEC-specific JSON Schema extension (not part of the
JSON Schema standard). When a property declares ``"x-oec-unit": "V"``,
this layer checks that an input shaped as ``{"value": …, "unit": …}`` is
dimensionally compatible with that expected unit via
:func:`~oec.kernel.units.normalize.is_compatible`.

The full link between declared schemas and dimensional validation will
be revisited when the first real skills (Sprint 04+) define their
``input.schema.json`` files in earnest; until then this layer only
inspects values that already look like :class:`~oec.kernel.units.quantity.QuantityValue`
dicts and optional ``x-oec-unit`` annotations.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import ValidationError

from oec.kernel.units.normalize import is_compatible
from oec.kernel.units.quantity import QuantityValue
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_QUANTITY_KEYS = frozenset({"value", "unit"})


class DimensionalValidator:
    """Validate physical-quantity-shaped inputs and optional ``x-oec-unit`` hints."""

    layer: ClassVar[str] = "dimensional"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        properties = skill.input_schema.get("properties")
        if not isinstance(properties, dict):
            properties = {}

        outcomes: list[ValidationOutcome] = []
        for field, raw in normalized_inputs.items():
            if not _is_quantity_dict(raw):
                continue

            try:
                quantity = QuantityValue(**raw)
            except ValidationError as exc:
                messages = [err["msg"] for err in exc.errors()]
                outcomes.append(
                    ValidationOutcome(
                        layer=self.layer,
                        severity=Severity.ERROR,
                        messages=messages or [str(exc)],
                        details={"field": field},
                    )
                )
                continue

            field_schema = properties.get(field)
            if not isinstance(field_schema, dict):
                continue
            expected_unit = field_schema.get("x-oec-unit")
            if not isinstance(expected_unit, str):
                continue

            if not is_compatible(quantity.unit, expected_unit):
                outcomes.append(
                    ValidationOutcome(
                        layer=self.layer,
                        severity=Severity.ERROR,
                        messages=[
                            f"field {field!r}: unit {quantity.unit!r} is dimensionally "
                            f"incompatible with expected unit {expected_unit!r}"
                        ],
                        details={
                            "field": field,
                            "unit": quantity.unit,
                            "expected_unit": expected_unit,
                        },
                    )
                )

        return outcomes


def _is_quantity_dict(value: object) -> bool:
    return isinstance(value, dict) and set(value.keys()) == _QUANTITY_KEYS
