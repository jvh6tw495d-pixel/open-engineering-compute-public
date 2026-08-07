from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class ReturnsValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(self, skill: LoadedSkill, normalized_inputs: dict[str, Any]):
        del skill
        r = normalized_inputs.get("returns")
        if not isinstance(r, list) or not r:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["returns must be a non-empty list"],
                )
            ]
        return []
