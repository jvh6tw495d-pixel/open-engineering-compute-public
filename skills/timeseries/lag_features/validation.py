from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class LagFeaturesValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        values = normalized_inputs.get("values")
        lags = normalized_inputs.get("lags")
        if not isinstance(values, list) or not values:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["values must be a non-empty 1D list"],
                )
            ]
        if any(not isinstance(x, (int, float)) for x in values):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["values must contain numbers only"],
                )
            ]
        if not isinstance(lags, list) or not lags:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["lags must be a non-empty list of non-negative ints"],
                )
            ]
        max_lag = max(lags)
        if len(values) <= max_lag:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["len(values) must exceed max(lags)"],
                )
            ]
        return []