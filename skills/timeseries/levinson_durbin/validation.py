from __future__ import annotations

import math
from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class LevinsonDurbinValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        acf = normalized_inputs.get("autocorrelation")
        if not isinstance(acf, list) or len(acf) < 2:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["autocorrelation must contain at least 2 values (r0, r1)"],
                )
            ]
        if not all(isinstance(v, int | float) and math.isfinite(v) for v in acf):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["autocorrelation must contain only finite numbers"],
                )
            ]
        if acf[0] <= 0:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["autocorrelation[0] (the process variance) must be positive"],
                )
            ]
        return []
