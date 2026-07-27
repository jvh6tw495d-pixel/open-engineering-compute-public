from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome
from oec.validation.physical import require_positive


class SocValidator:
    layer: ClassVar[str] = "physical"

    def validate(self, skill: LoadedSkill, normalized_inputs: dict[str, Any]):
        del skill
        outcomes = []
        for field in ("capacity",):
            if field in normalized_inputs:
                raw = normalized_inputs[field]
                value = raw["value"] if isinstance(raw, dict) else raw
                o = require_positive(field, float(value))
                if o.severity is Severity.ERROR:
                    outcomes.append(o)
        soc = normalized_inputs.get("soc")
        if isinstance(soc, int | float) and not (0.0 <= float(soc) <= 1.0):
            outcomes.append(
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=[f"soc must be in [0,1], got {soc}"],
                )
            )
        return outcomes
