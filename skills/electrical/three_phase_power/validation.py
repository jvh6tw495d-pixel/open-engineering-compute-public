"""Skill-specific validation for electrical.three_phase_power (plan section 14.2).

JSON Schema (``input.schema.json``) and ``DimensionalValidator``
(``validation.dimensional: true``, ``x-oec-unit``) already cover types,
required keys, and unit compatibility. This module checks what neither
can express: physical positivity of voltage/current (a zero or negative
magnitude is not a real three-phase system), via
``oec.validation.physical``'s reusable helpers — the same pattern
``physical: true`` documents for every skill, per
``docs/architecture/adr/0014-validator-auto-discovery-and-sdk.md``.

Discovered and wired via ``validation.mathematical: true`` (ADR 0014's
auto-discovery only gates on that flag, not ``physical``); this
validator's own ``layer`` is ``"physical"`` since that's what its checks
actually are.
"""

from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome
from oec.validation.physical import require_positive


class ThreePhasePowerValidator:
    """Physical-domain checks JSON Schema and dimensional checks can't express."""

    layer: ClassVar[str] = "physical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill  # interface contract; unused here
        outcomes: list[ValidationOutcome] = []

        voltage = normalized_inputs.get("voltage_line_to_line")
        if isinstance(voltage, dict) and isinstance(voltage.get("value"), int | float):
            outcome = require_positive("voltage_line_to_line", float(voltage["value"]))
            if outcome.severity is not Severity.OK:
                outcomes.append(outcome)

        current = normalized_inputs.get("current_line")
        if isinstance(current, dict) and isinstance(current.get("value"), int | float):
            outcome = require_positive("current_line", float(current["value"]))
            if outcome.severity is not Severity.OK:
                outcomes.append(outcome)

        return outcomes
