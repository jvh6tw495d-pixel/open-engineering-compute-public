from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class MatrixPropertiesValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(self, skill: LoadedSkill, normalized_inputs: dict[str, Any]):
        del skill
        a = normalized_inputs.get("A")
        if not isinstance(a, list) or not a or not isinstance(a[0], list) or not a[0]:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["A must be a non-empty 2D list"],
                )
            ]
        n_cols = len(a[0])
        if any(not isinstance(row, list) or len(row) != n_cols for row in a):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["A rows must have equal length"],
                )
            ]
        return []
