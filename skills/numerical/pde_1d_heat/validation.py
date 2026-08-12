"""Mathematical validation for numerical.pde_1d_heat."""

from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class Pde1dHeatValidator:
    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        n = int(normalized_inputs.get("n_intervals", 20))
        initial = normalized_inputs.get("initial")
        if initial is not None and len(initial) != n + 1:
            return [
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[f"initial length must be n_intervals+1={n + 1}, got {len(initial)}"],
                )
            ]
        return []
