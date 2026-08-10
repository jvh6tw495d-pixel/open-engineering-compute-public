from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class MlpClassifierValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        x = normalized_inputs.get("x")
        y = normalized_inputs.get("y")
        if not isinstance(x, list) or not x or not isinstance(y, list) or len(x) != len(y):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["x and y must be lists of equal length"],
                )
            ]
        n_classes = int(normalized_inputs.get("n_classes", 2))
        if n_classes < 2:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["n_classes must be >= 2"],
                )
            ]
        return []
