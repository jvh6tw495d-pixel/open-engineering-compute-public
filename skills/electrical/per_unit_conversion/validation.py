"""Skill-specific validation for electrical.per_unit_conversion."""

from __future__ import annotations

from typing import Any, ClassVar

from oec.kernel.units.normalize import normalize
from oec.kernel.units.quantity import QuantityValue
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome
from oec.validation.physical import require_positive

_LAYER = "physical"

_EXPECTED_UNIT = {
    "impedance": "ohm",
    "voltage": "V",
    "current": "A",
    "power": "W",
}


class PerUnitConversionValidator:
    """Cross-field operation rules, unit kind for free-form value, positivity."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        outcomes: list[ValidationOutcome] = []

        operation = normalized_inputs.get("operation")
        kind = normalized_inputs.get("quantity_kind")
        has_value = "value" in normalized_inputs
        has_pu = "value_pu" in normalized_inputs
        has_new_v = "new_voltage_base" in normalized_inputs
        has_new_s = "new_power_base" in normalized_inputs

        if operation in ("to_per_unit", "from_per_unit") and kind not in _EXPECTED_UNIT:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        f"operation={operation!r} requires 'quantity_kind' "
                        "(impedance|voltage|current|power)"
                    ],
                )
            )
        if operation == "to_per_unit":
            if not has_value:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=["operation='to_per_unit' requires 'value'"],
                    )
                )
            if has_pu:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=["'value_pu' is not accepted with operation='to_per_unit'"],
                    )
                )
            if has_value and kind in _EXPECTED_UNIT:
                outcomes.extend(_check_value_unit(normalized_inputs["value"], kind))
        elif operation == "from_per_unit":
            if not has_pu:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=["operation='from_per_unit' requires 'value_pu'"],
                    )
                )
            if has_value:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=["'value' is not accepted with operation='from_per_unit'"],
                    )
                )
        elif operation == "change_base":
            if not has_pu:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=["operation='change_base' requires 'value_pu'"],
                    )
                )
            if not (has_new_v and has_new_s):
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=[
                            "operation='change_base' requires 'new_voltage_base' "
                            "and 'new_power_base'"
                        ],
                    )
                )
            if has_value:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=["'value' is not accepted with operation='change_base'"],
                    )
                )

        for field in ("voltage_base", "power_base", "new_voltage_base", "new_power_base"):
            raw = normalized_inputs.get(field)
            if isinstance(raw, dict) and isinstance(raw.get("value"), int | float):
                outcome = require_positive(field, float(raw["value"]))
                if outcome.severity is not Severity.OK:
                    outcomes.append(outcome)

        return outcomes


def _check_value_unit(raw: Any, kind: str) -> list[ValidationOutcome]:
    if not isinstance(raw, dict) or not isinstance(raw.get("unit"), str):
        return [
            ValidationOutcome(
                layer=_LAYER,
                severity=Severity.ERROR,
                messages=["'value' must be a QuantityValue {value, unit}"],
            )
        ]
    expected = _EXPECTED_UNIT[kind]
    try:
        quantity = QuantityValue(value=float(raw["value"]), unit=str(raw["unit"]))
        normalize(quantity, to_unit=expected)
    except Exception as exc:  # noqa: BLE001 — surface as validation, not crash
        return [
            ValidationOutcome(
                layer=_LAYER,
                severity=Severity.ERROR,
                messages=[
                    f"'value' unit must be convertible to {expected!r} for "
                    f"quantity_kind={kind!r}: {exc}"
                ],
            )
        ]
    return []
