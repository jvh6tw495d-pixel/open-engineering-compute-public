from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class MorrisValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        bounds = normalized_inputs.get("bounds")
        coeffs = normalized_inputs.get("coeffs")
        if not isinstance(bounds, list) or not isinstance(coeffs, list):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["bounds and coeffs required"],
                )
            ]
        if len(bounds) != len(coeffs):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["coeffs length must match bounds"],
                )
            ]
        return []
