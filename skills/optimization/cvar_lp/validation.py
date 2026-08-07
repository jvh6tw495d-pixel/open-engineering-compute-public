from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class CvarLpValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        alpha = normalized_inputs.get("alpha")
        if not isinstance(alpha, (int, float)) or not (0 < float(alpha) < 1):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["alpha must be in (0,1)"],
                )
            ]
        scenarios = normalized_inputs.get("loss_scenarios")
        if not isinstance(scenarios, list) or not scenarios:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["loss_scenarios must be non-empty"],
                )
            ]
        return []
