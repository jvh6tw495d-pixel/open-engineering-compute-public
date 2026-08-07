from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class MonteCarloValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(self, skill: LoadedSkill, normalized_inputs: dict[str, Any]):
        del skill
        n = normalized_inputs.get("n_samples")
        low = normalized_inputs.get("low")
        high = normalized_inputs.get("high")
        messages: list[str] = []
        if not isinstance(n, int) or n < 1:
            messages.append("n_samples must be a positive integer")
        if not isinstance(low, int | float) or not isinstance(high, int | float):
            messages.append("low and high must be numbers")
        elif float(high) <= float(low):
            messages.append("high must be > low")
        expr = normalized_inputs.get("expression")
        if not isinstance(expr, str) or not expr.strip():
            messages.append("expression must be a non-empty string")
        if messages:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=messages,
                )
            ]
        return []
