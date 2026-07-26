from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class QpValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(self, skill: LoadedSkill, normalized_inputs: dict[str, Any]):
        del skill
        q, c = normalized_inputs.get("Q"), normalized_inputs.get("c")
        if not isinstance(q, list) or not q or not isinstance(q[0], list):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["Q must be a non-empty 2D array"],
                )
            ]
        n = len(q)
        if any(not isinstance(row, list) or len(row) != n for row in q):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["Q must be square"],
                )
            ]
        if not isinstance(c, list) or len(c) != n:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["c length must equal Q dimension"],
                )
            ]
        return []
