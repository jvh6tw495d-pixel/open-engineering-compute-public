from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class RobustLpValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        unc = normalized_inputs.get("rhs_uncertainty")
        if not isinstance(unc, dict) or not unc:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["rhs_uncertainty must be a non-empty map"],
                )
            ]
        if any(not isinstance(v, (int, float)) or float(v) < 0 for v in unc.values()):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["radii must be non-negative numbers"],
                )
            ]
        return []
