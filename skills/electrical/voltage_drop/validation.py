"""Skill-specific validation for electrical.voltage_drop (plan section 14.2).

Cross-field presence rules (load type vs current/power; resistance path
vs material+cross_section) plus physical positivity. Discovered via
``validation.mathematical: true`` (ADR 0014); ``layer`` is ``physical``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome
from oec.validation.physical import require_positive

_LAYER = "physical"


class VoltageDropValidator:
    """Cross-field and physical-domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        outcomes: list[ValidationOutcome] = []

        load_type = normalized_inputs.get("load_type")
        has_current = "current" in normalized_inputs
        has_power = "power" in normalized_inputs

        if load_type == "current":
            if not has_current:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=["load_type='current' requires 'current'"],
                    )
                )
            if has_power:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=[
                            "'power' is only accepted with load_type='power' "
                            "(current is already given)"
                        ],
                    )
                )
        elif load_type == "power":
            if not has_power:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=["load_type='power' requires 'power'"],
                    )
                )
            if has_current:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=[
                            "'current' is only accepted with load_type='current' "
                            "(current is derived from power)"
                        ],
                    )
                )

        has_r = "resistance_per_length" in normalized_inputs
        has_material = "material" in normalized_inputs
        has_section = "cross_section" in normalized_inputs

        if has_r and (has_material or has_section):
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        "give either 'resistance_per_length' or "
                        "('material' + 'cross_section'), not both"
                    ],
                )
            )
        elif not has_r and not (has_material and has_section):
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        "conductor resistance requires either "
                        "'resistance_per_length' or both 'material' and "
                        "'cross_section'"
                    ],
                )
            )
        if has_material and not has_section:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["'material' requires 'cross_section'"],
                )
            )
        if has_section and not has_material:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["'cross_section' requires 'material'"],
                )
            )

        for field in (
            "voltage_reference",
            "length",
            "current",
            "power",
            "resistance_per_length",
            "cross_section",
        ):
            raw = normalized_inputs.get(field)
            if isinstance(raw, dict) and isinstance(raw.get("value"), int | float):
                outcome = require_positive(field, float(raw["value"]))
                if outcome.severity is not Severity.OK:
                    outcomes.append(outcome)

        reactance = normalized_inputs.get("reactance_per_length")
        if (
            isinstance(reactance, dict)
            and isinstance(reactance.get("value"), int | float)
            and float(reactance["value"]) < 0.0
        ):
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        f"field 'reactance_per_length' must be >= 0, got {reactance['value']}"
                    ],
                    details={"field": "reactance_per_length", "value": reactance["value"]},
                )
            )

        return outcomes
