from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class ParetoLpValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        a = normalized_inputs.get("objective_a")
        b = normalized_inputs.get("objective_b")
        if not isinstance(a, dict) or not a or not isinstance(b, dict) or not b:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["objective_a and objective_b must be non-empty coeff maps"],
                )
            ]
        n = normalized_inputs.get("n_points", 11)
        if not isinstance(n, int) or n < 2:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["n_points must be an integer >= 2"],
                )
            ]
        return []
