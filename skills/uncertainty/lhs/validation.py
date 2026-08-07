from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class LhsValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        bounds = normalized_inputs.get("bounds")
        if not isinstance(bounds, list) or not bounds:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["bounds must be non-empty"],
                )
            ]
        for pair in bounds:
            if not isinstance(pair, list) or len(pair) != 2 or not (pair[0] < pair[1]):
                return [
                    ValidationOutcome(
                        layer=self.layer,
                        severity=Severity.ERROR,
                        messages=["each bound must satisfy low < high"],
                    )
                ]
        n = normalized_inputs.get("n_samples")
        if not isinstance(n, int) or n < 1:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["n_samples must be a positive integer"],
                )
            ]
        return []
