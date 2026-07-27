from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class ForecastSimpleValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        series = normalized_inputs.get("series")
        if not isinstance(series, list) or not series:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["series must be a non-empty 1D list"],
                )
            ]
        if any(not isinstance(x, (int, float)) for x in series):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["series must contain numbers only"],
                )
            ]
        steps_ahead = normalized_inputs.get("steps_ahead")
        if not isinstance(steps_ahead, int) or steps_ahead < 1:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["steps_ahead must be a positive integer"],
                )
            ]
        method = normalized_inputs.get("method")
        if method == "seasonal_naive":
            period = normalized_inputs.get("period")
            if not isinstance(period, int) or period < 1:
                return [
                    ValidationOutcome(
                        layer=self.layer,
                        severity=Severity.ERROR,
                        messages=["seasonal_naive requires period >= 1"],
                    )
                ]
            if len(series) < period:
                return [
                    ValidationOutcome(
                        layer=self.layer,
                        severity=Severity.ERROR,
                        messages=["seasonal_naive requires len(series) >= period"],
                    )
                ]
        return []