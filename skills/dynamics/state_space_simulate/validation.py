from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class StateSpaceValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        a = normalized_inputs.get("A")
        if not isinstance(a, list) or not a or len(a) != len(a[0]):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["A must be square"],
                )
            ]
        if float(normalized_inputs.get("dt", 0)) <= 0:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["dt must be > 0"],
                )
            ]
        return []
