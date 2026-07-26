from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class LinearSolveValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(self, skill: LoadedSkill, normalized_inputs: dict[str, Any]):
        del skill
        a, b = normalized_inputs.get("A"), normalized_inputs.get("b")
        if not isinstance(a, list) or not a or not isinstance(a[0], list):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["A must be a non-empty 2D list"],
                )
            ]
        n = len(a)
        if any(not isinstance(row, list) or len(row) != n for row in a):
            return [
                ValidationOutcome(
                    layer=self.layer, severity=Severity.ERROR, messages=["A must be square"]
                )
            ]
        if not isinstance(b, list) or len(b) != n:
            return [
                ValidationOutcome(
                    layer=self.layer, severity=Severity.ERROR, messages=["b length must equal n"]
                )
            ]
        return []
