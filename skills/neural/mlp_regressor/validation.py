from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class MlpRegressorValidator:
    """Cross-field checks for tabular MLP regression."""

    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        x = normalized_inputs.get("x")
        y = normalized_inputs.get("y")
        if not isinstance(x, list) or not x or not isinstance(x[0], list):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["x must be a non-empty 2D list"],
                )
            ]
        if not isinstance(y, list) or len(y) != len(x):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["y must be a list with len(y) == rows(x)"],
                )
            ]
        return []
