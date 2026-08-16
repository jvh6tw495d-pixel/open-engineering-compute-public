from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class BacktestValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        series = normalized_inputs.get("series")
        if not isinstance(series, list) or len(series) < 2:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["series must contain at least 2 samples"],
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
        n_eval = normalized_inputs.get("n_evaluations")
        if n_eval is None:
            n_eval = len(series) - 1
        if not isinstance(n_eval, int) or n_eval < 1:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["n_evaluations must be a positive integer"],
                )
            ]
        if n_eval >= len(series):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["n_evaluations must be < len(series)"],
                )
            ]
        if normalized_inputs.get("method") == "seasonal_naive":
            period = normalized_inputs.get("period")
            if not isinstance(period, int) or period < 1 or period > len(series):
                return [
                    ValidationOutcome(
                        layer=self.layer,
                        severity=Severity.ERROR,
                        messages=["seasonal_naive requires 1 <= period <= len(series)"],
                    )
                ]
        return []
