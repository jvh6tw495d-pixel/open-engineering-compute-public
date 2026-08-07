from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class MinStorageCapacityValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(self, skill: LoadedSkill, normalized_inputs: dict[str, Any]):
        del skill
        load = normalized_inputs.get("load", [])
        pv = normalized_inputs.get("pv", [])
        outcomes: list[ValidationOutcome] = []
        if not isinstance(load, list) or not isinstance(pv, list):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["load and pv must be lists"],
                )
            ]
        if len(load) != len(pv):
            outcomes.append(
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=[f"load length ({len(load)}) must equal pv length ({len(pv)})"],
                )
            )
        soc_min = float(normalized_inputs.get("soc_min", 0.0))
        soc_max = float(normalized_inputs.get("soc_max", 1.0))
        if soc_min > soc_max:
            outcomes.append(
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["soc_min must be <= soc_max"],
                )
            )
        return outcomes
