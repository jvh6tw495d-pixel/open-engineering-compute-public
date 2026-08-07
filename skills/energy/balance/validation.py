from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class BalanceValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(self, skill: LoadedSkill, normalized_inputs: dict[str, Any]):
        del skill
        ein = normalized_inputs.get("energy_in", [])
        eout = normalized_inputs.get("energy_out", [])
        if not isinstance(ein, list) or not isinstance(eout, list):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["energy_in/out must be lists"],
                )
            ]
        if len(ein) == 0 and len(eout) == 0:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["provide energy_in and/or energy_out"],
                )
            ]
        return []
