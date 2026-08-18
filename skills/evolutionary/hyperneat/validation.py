from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_FITNESS = frozenset({"xor", "tabular_regression", "tabular_classification"})


class HyperNeatValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        fitness = normalized_inputs.get("fitness")
        if fitness not in _FITNESS:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["fitness must be xor, tabular_regression, or tabular_classification"],
                )
            ]
        if fitness == "xor":
            return []
        x = normalized_inputs.get("x")
        y = normalized_inputs.get("y")
        if not isinstance(x, list) or not isinstance(y, list) or not x:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["tabular fitness requires non-empty x and y"],
                )
            ]
        return []
