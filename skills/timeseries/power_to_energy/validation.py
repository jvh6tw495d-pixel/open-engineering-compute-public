from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class PowerEnergyValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(self, skill: LoadedSkill, normalized_inputs: dict[str, Any]):
        del skill
        ts, p = normalized_inputs.get("timestamps"), normalized_inputs.get("power")
        if not isinstance(ts, list) or not isinstance(p, list) or len(ts) != len(p) or len(ts) < 2:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["timestamps/power must be equal length >= 2"],
                )
            ]
        return []
