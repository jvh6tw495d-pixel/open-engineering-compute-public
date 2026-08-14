from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class LeastSquaresValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        a = normalized_inputs.get("A")
        b = normalized_inputs.get("b")
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
        if not isinstance(b, list) or not b:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["b must be a non-empty 1D list"],
                )
            ]
        if len(b) != len(a):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["len(b) must equal number of rows of A"],
                )
            ]
        return []
