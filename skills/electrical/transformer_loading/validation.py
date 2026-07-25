"""Skill-specific validation for electrical.transformer_loading."""

from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome
from oec.validation.physical import require_positive

_LAYER = "physical"


class TransformerLoadingValidator:
    """Cross-field load_type rules and physical positivity."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        outcomes: list[ValidationOutcome] = []

        load_type = normalized_inputs.get("load_type")
        has_s = "load_apparent_power" in normalized_inputs
        has_i = "load_current" in normalized_inputs
        has_ir = "rated_current" in normalized_inputs

        if load_type == "apparent_power":
            if not has_s:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=["load_type='apparent_power' requires 'load_apparent_power'"],
                    )
                )
            if has_i or has_ir:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=[
                            "'load_current'/'rated_current' are only accepted with "
                            "load_type='current'"
                        ],
                    )
                )
        elif load_type == "current":
            if not has_i or not has_ir:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=[
                            "load_type='current' requires both 'load_current' and 'rated_current'"
                        ],
                    )
                )
            if has_s:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=[
                            "'load_apparent_power' is only accepted with load_type='apparent_power'"
                        ],
                    )
                )

        for field in (
            "rated_apparent_power",
            "load_apparent_power",
            "load_current",
            "rated_current",
        ):
            raw = normalized_inputs.get(field)
            if isinstance(raw, dict) and isinstance(raw.get("value"), int | float):
                outcome = require_positive(field, float(raw["value"]))
                if outcome.severity is not Severity.OK:
                    outcomes.append(outcome)

        threshold = normalized_inputs.get("overload_threshold_percent")
        if isinstance(threshold, int | float) and float(threshold) <= 0.0:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        f"field 'overload_threshold_percent' must be positive, got {threshold}"
                    ],
                )
            )

        return outcomes
