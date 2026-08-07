from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class AutocorrelationValidator:
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
        nlags = normalized_inputs.get("nlags")
        if not isinstance(nlags, int) or nlags < 1:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["nlags must be a positive integer"],
                )
            ]
        if nlags >= len(series):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["nlags must be < len(series)"],
                )
            ]
        if len(set(series)) == 1:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["series has zero variance; autocorrelation is undefined"],
                )
            ]
        return []
