"""Dimensional validation of physical quantities in skill inputs (plan section 12.2).

``x-oec-unit`` is an OEC-specific JSON Schema extension (not part of the
JSON Schema standard). When a property declares ``"x-oec-unit": "V"``,
this layer checks that an input shaped as ``{"value": …, "unit": …}`` is
dimensionally compatible with that expected unit via
:func:`~oec.kernel.units.normalize.is_compatible`.

This is the *only* place that check happens (ADR 0016): once this
validator reports no `ERROR` outcome, `ExecutionService.execute()`
trusts every ``x-oec-unit`` field is convertible and hands the actual
conversion to :func:`oec.execution.normalization.apply_dimensional_normalization`
-- a pure, non-failing transform that never re-checks compatibility
itself, so a mismatch is reported exactly once, here.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import ValidationError

from oec.kernel.units.normalize import is_compatible
from oec.kernel.units.quantity import QuantityValue
from oec.kernel.units.schema import declared_units, is_quantity_dict
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class DimensionalValidator:
    """Validate physical-quantity-shaped inputs and optional ``x-oec-unit`` hints."""

    layer: ClassVar[str] = "dimensional"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        properties = skill.input_schema.get("properties")
        if not isinstance(properties, dict):
            properties = {}
        expected_units = declared_units(properties)

        outcomes: list[ValidationOutcome] = []
        for field, raw in normalized_inputs.items():
            if not is_quantity_dict(raw):
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

            expected_unit = expected_units.get(field)
            if expected_unit is None:
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
