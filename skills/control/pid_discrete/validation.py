from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class PidValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        r = normalized_inputs.get("reference")
        m = normalized_inputs.get("measurement")
        if not isinstance(r, list) or not isinstance(m, list) or len(r) != len(m) or not r:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["reference and measurement must be equal non-empty lists"],
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
