from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class EvolutionaryBenchmarkValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        if not isinstance(normalized_inputs.get("variables"), list):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["variables must be a list"],
                )
            ]
        mode = normalized_inputs.get("mode", "single")
        if mode == "multi" and len(normalized_inputs.get("variables") or []) < 2:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["multi mode requires at least 2 variables"],
                )
            ]
        return []
