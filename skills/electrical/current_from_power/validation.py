"""Skill-specific validation for electrical.current_from_power (plan section 14.2).

JSON Schema and ``DimensionalValidator`` already cover types, required
keys, unit compatibility, and ``power_factor``/``efficiency`` ranges.
This module checks what neither can express: the cross-field
``power_factor`` presence rule between ``power_type`` values (mirrors
``mathematics.solve_root``'s ``method``/``bracket`` presence pattern),
and physical positivity via ``oec.validation.physical``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome
from oec.validation.physical import require_positive

_LAYER = "physical"


class CurrentFromPowerValidator:
    """Cross-field and physical-domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill  # interface contract; unused here
        outcomes: list[ValidationOutcome] = []

        power_type = normalized_inputs.get("power_type")
        has_power_factor = "power_factor" in normalized_inputs

        if power_type == "active" and not has_power_factor:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["power_type='active' requires 'power_factor'"],
                )
            )
        if power_type == "apparent" and has_power_factor:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        "'power_factor' is only accepted with power_type='active' "
                        "(apparent power alone already fixes the current)"
                    ],
                )
            )

        power = normalized_inputs.get("power")
        if isinstance(power, dict) and isinstance(power.get("value"), int | float):
            outcome = require_positive("power", float(power["value"]))
            if outcome.severity is not Severity.OK:
                outcomes.append(outcome)

        voltage = normalized_inputs.get("voltage")
        if isinstance(voltage, dict) and isinstance(voltage.get("value"), int | float):
            outcome = require_positive("voltage", float(voltage["value"]))
            if outcome.severity is not Severity.OK:
                outcomes.append(outcome)

        return outcomes
