from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class NeuralEvaluateValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        x = normalized_inputs.get("x")
        y = normalized_inputs.get("y")
        if not isinstance(x, list) or not isinstance(y, list) or len(x) != len(y):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["x and y must be lists of equal length"],
                )
            ]
        if not isinstance(normalized_inputs.get("checkpoint"), dict):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["checkpoint must be an object"],
                )
            ]
        return []
