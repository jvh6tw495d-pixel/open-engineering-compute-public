from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class LengthMatchValidator:
    layer: ClassVar[str] = "mathematical"
    pairs: ClassVar[list[tuple[str, str]]] = [("timestamps", "values")]

    def validate(self, skill: LoadedSkill, normalized_inputs: dict[str, Any]):
        del skill
        for a, b in self.pairs:
            ta, tb = normalized_inputs.get(a), normalized_inputs.get(b)
            if not isinstance(ta, list) or not isinstance(tb, list) or len(ta) != len(tb) or not ta:
                return [
                    ValidationOutcome(
                        layer=self.layer,
                        severity=Severity.ERROR,
                        messages=[f"{a}/{b} must be same-length non-empty lists"],
                    )
                ]
        return []
