"""Dimensional validation of physical quantities at skill boundaries.

``x-oec-unit`` is an OEC-specific JSON Schema extension (not part of the
JSON Schema standard). When a property declares ``"x-oec-unit": "V"``,
this layer checks that an input shaped as ``{"value": …, "unit": …}`` is
dimensionally compatible with that expected unit via
:func:`~oec.kernel.units.normalize.is_compatible`.

``DimensionalValidator`` checks inputs are convertible before the execution
service normalizes them. ``ResultDimensionalValidator`` checks declared
quantity outputs after execution. Output quantities are not normalized: the
declared ``x-oec-unit`` is their public canonical unit, so a different (even
compatible) unit is an invalid result rather than a value to rewrite.
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
            expected_unit = expected_units.get(field)
            candidates = (
                [(field, raw)]
                if is_quantity_dict(raw)
                else [
                    (f"{field}[{index}]", item)
                    for index, item in enumerate(raw)
                    if is_quantity_dict(item)
                ]
                if isinstance(raw, list)
                else []
            )
            for location, candidate in candidates:
                try:
                    quantity = QuantityValue(**candidate)
                except ValidationError as exc:
                    messages = [err["msg"] for err in exc.errors()]
                    outcomes.append(
                        ValidationOutcome(
                            layer=self.layer,
                            severity=Severity.ERROR,
                            messages=messages or [str(exc)],
                            details={"field": location},
                        )
                    )
                    continue

                if expected_unit is not None and not is_compatible(quantity.unit, expected_unit):
                    outcomes.append(
                        ValidationOutcome(
                            layer=self.layer,
                            severity=Severity.ERROR,
                            messages=[
                                f"field {location!r}: unit {quantity.unit!r} is dimensionally "
                                f"incompatible with expected unit {expected_unit!r}"
                            ],
                            details={
                                "field": location,
                                "unit": quantity.unit,
                                "expected_unit": expected_unit,
                            },
                        )
                    )

        return outcomes


class ResultDimensionalValidator:
    """Validate declared physical outputs without changing their serialization.

    A field declaring ``x-oec-unit`` is a physical output contract.  When it
    is present in the result, it must be an *exactly* ``{value, unit}``
    QuantityValue-shaped mapping, validate as a public ``QuantityValue``, and
    carry the declared canonical unit.  Requiring the exact shape here is
    intentional: ``is_quantity_dict`` rejects extra keys, and treating those
    mappings as ordinary output objects would let malformed quantities evade
    the result-side dimensional gate.

    Exact QuantityValue-shaped fields without an ``x-oec-unit`` declaration
    are still parsed, so invalid quantity DTOs cannot be emitted as otherwise
    valid results.  Other output structures are left untouched for backwards
    compatibility with non-physical skills.

    A field whose JSON Schema ``type`` is ``array`` is a different contract:
    a bare numeric series sharing one canonical unit (declared once on the
    array, per :mod:`scripts.audit_physical_units`), not a single
    QuantityValue. Each item must be a plain number instead of a
    ``{value, unit}`` mapping.
    """

    layer: ClassVar[str] = "dimensional"

    def validate(
        self,
        skill: LoadedSkill,
        normalized_inputs: dict[str, Any],
        result: dict[str, Any],
        diagnostics: dict[str, Any],
    ) -> list[ValidationOutcome]:
        del normalized_inputs, diagnostics  # interface contract; unused here
        properties = skill.output_schema.get("properties")
        if not isinstance(properties, dict):
            properties = {}
        expected_units = declared_units(properties)
        for field, field_schema in properties.items():
            if field in expected_units or not isinstance(field_schema, dict):
                continue
            unit_schema = field_schema.get("properties", {}).get("unit", {})
            if isinstance(unit_schema, dict) and isinstance(unit_schema.get("const"), str):
                expected_units[field] = unit_schema["const"]

        outcomes: list[ValidationOutcome] = []
        for field, expected_unit in expected_units.items():
            # Required-output handling belongs to InvariantValidator. Optional
            # physical outputs have no quantity to validate when absent.
            if field not in result:
                continue
            field_schema = properties.get(field)
            if result[field] is None and isinstance(field_schema, dict):
                variants = field_schema.get("oneOf", [])
                declared_type = field_schema.get("type")
                allows_null = declared_type == "null" or (
                    isinstance(declared_type, list) and "null" in declared_type
                )
                if allows_null or any(
                    isinstance(variant, dict) and variant.get("type") == "null"
                    for variant in variants
                ):
                    continue
            if isinstance(field_schema, dict) and field_schema.get("type") == "array":
                outcomes.extend(self._validate_declared_array_quantity(field, result[field]))
                continue
            outcomes.extend(self._validate_declared_quantity(field, result[field], expected_unit))

        # An exact DTO shape is an unambiguous declaration of a quantity even
        # without a schema unit hint. Validate it, but do not impose a unit on
        # arbitrary, non-physical output objects.
        for field, raw in result.items():
            if field not in expected_units and is_quantity_dict(raw):
                outcomes.extend(self._validate_quantity(field, raw))

        return outcomes

    def _validate_declared_quantity(
        self, field: str, raw: Any, expected_unit: str
    ) -> list[ValidationOutcome]:
        if not is_quantity_dict(raw):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=[
                        f"field {field!r}: declared physical output must be an exact "
                        "QuantityValue object with keys {'value', 'unit'}"
                    ],
                    details={
                        "field": field,
                        "expected_unit": expected_unit,
                        "reason": "malformed_quantity_output",
                    },
                )
            ]

        outcomes = self._validate_quantity(field, raw, expected_unit=expected_unit)
        return outcomes

    def _validate_declared_array_quantity(self, field: str, raw: Any) -> list[ValidationOutcome]:
        if not isinstance(raw, list) or not all(
            isinstance(item, (int, float)) and not isinstance(item, bool) for item in raw
        ):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=[
                        f"field {field!r}: declared physical series must be a plain array "
                        "of numbers"
                    ],
                    details={"field": field, "reason": "malformed_quantity_series_output"},
                )
            ]
        return []

    def _validate_quantity(
        self, field: str, raw: dict[str, Any], *, expected_unit: str | None = None
    ) -> list[ValidationOutcome]:
        try:
            quantity = QuantityValue(**raw)
        except Exception as exc:  # noqa: BLE001 -- third-party unit parsing can raise non-Pydantic errors
            messages = (
                [err["msg"] for err in exc.errors()] if isinstance(exc, ValidationError) else []
            )
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=messages or [str(exc)],
                    details={"field": field, "reason": "invalid_quantity_output"},
                )
            ]

        if expected_unit is not None and quantity.unit != expected_unit:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=[
                        f"field {field!r}: output unit {quantity.unit!r} must equal declared "
                        f"canonical unit {expected_unit!r}"
                    ],
                    details={
                        "field": field,
                        "unit": quantity.unit,
                        "expected_unit": expected_unit,
                        "reason": "noncanonical_output_unit",
                    },
                )
            ]

        return []
