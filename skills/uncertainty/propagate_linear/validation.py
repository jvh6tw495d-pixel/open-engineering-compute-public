from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class PropagateLinearValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        cov = normalized_inputs.get("covariance")
        if not isinstance(cov, list) or not cov or not isinstance(cov[0], list):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["covariance must be a square matrix"],
                )
            ]
        n = len(cov)
        if any(not isinstance(row, list) or len(row) != n for row in cov):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["covariance must be square"],
                )
            ]
        return []
