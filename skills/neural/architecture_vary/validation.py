from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_MUT = frozenset({"widen", "deepen", "swap_activation"})
_CROSS = frozenset({"one_point_chain"})


class ArchitectureVaryValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        mode = normalized_inputs.get("mode")
        operator = normalized_inputs.get("operator")
        if mode == "mutate" and operator not in _MUT:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["mutate operator must be widen, deepen, or swap_activation"],
                )
            ]
        if mode == "crossover" and operator not in _CROSS:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["crossover operator must be one_point_chain"],
                )
            ]
        return []
