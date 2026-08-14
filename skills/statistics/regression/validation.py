from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class RegressionValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        x = normalized_inputs.get("x")
        y = normalized_inputs.get("y")
        if not isinstance(x, list) or not x or not isinstance(x[0], list) or not x[0]:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["x must be a non-empty 2D list"],
                )
            ]
        n_cols = len(x[0])
        if any(not isinstance(row, list) or len(row) != n_cols for row in x):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["x rows must have equal length"],
                )
            ]
        if not isinstance(y, list) or not y:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["y must be a non-empty 1D list"],
                )
            ]
        if len(y) != len(x):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["len(y) must equal number of rows of x"],
                )
            ]
        if len(x) <= n_cols:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["regression requires n_samples > n_features"],
                )
            ]
        return []
