from __future__ import annotations

import math
from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class IntervalsValidator:
    """Cross-field checks for statistics.intervals 0.2.0."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        if "known_variance" in normalized_inputs:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=[
                        "known_variance was removed; use population_standard_deviation"
                    ],
                )
            ]
        samples = normalized_inputs.get("samples")
        if not isinstance(samples, list) or not samples:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["samples must be a non-empty 1D list"],
                )
            ]
        if any(not isinstance(x, (int, float)) or not math.isfinite(float(x)) for x in samples):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["samples must contain finite numbers only"],
                )
            ]
        sigma = normalized_inputs.get("population_standard_deviation")
        if sigma is not None:
            if not isinstance(sigma, (int, float)) or not math.isfinite(float(sigma)):
                return [
                    ValidationOutcome(
                        layer=self.layer,
                        severity=Severity.ERROR,
                        messages=["population_standard_deviation must be finite"],
                    )
                ]
            if float(sigma) <= 0.0:
                return [
                    ValidationOutcome(
                        layer=self.layer,
                        severity=Severity.ERROR,
                        messages=["population_standard_deviation must be > 0"],
                    )
                ]
        elif len(samples) < 2:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=[
                        "Student-t CI requires n >= 2 "
                        "(or supply population_standard_deviation)"
                    ],
                )
            ]
        return []
