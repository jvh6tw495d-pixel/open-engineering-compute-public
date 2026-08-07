"""Skill-specific validation for electrical.power_factor_correction."""

from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome
from oec.validation.physical import require_positive

_LAYER = "physical"


class PowerFactorCorrectionValidator:
    """Cross-field connection rules and physical positivity."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        outcomes: list[ValidationOutcome] = []

        phase_count = normalized_inputs.get("phase_count")
        connection = normalized_inputs.get("connection")

        if phase_count == 1 and connection != "single_phase":
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        f"phase_count=1 requires connection='single_phase' (got {connection!r})"
                    ],
                )
            )
        if phase_count == 3 and connection not in ("delta", "star"):
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        f"phase_count=3 requires connection='delta' or 'star' (got {connection!r})"
                    ],
                )
            )

        existing = normalized_inputs.get("existing_power_factor")
        desired = normalized_inputs.get("desired_power_factor")
        if (
            isinstance(existing, int | float)
            and isinstance(desired, int | float)
            and float(desired) < float(existing)
        ):
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        "desired_power_factor must be >= existing_power_factor "
                        f"(got desired={desired}, existing={existing}); "
                        "this skill sizes a capacitor bank to raise PF, "
                        "not lower it"
                    ],
                )
            )

        for field in ("active_power", "voltage", "frequency"):
            raw = normalized_inputs.get(field)
            if isinstance(raw, dict) and isinstance(raw.get("value"), int | float):
                outcome = require_positive(field, float(raw["value"]))
                if outcome.severity is not Severity.OK:
                    outcomes.append(outcome)

        return outcomes
