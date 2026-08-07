from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class RootSystemValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(self, skill: LoadedSkill, normalized_inputs: dict[str, Any]):
        del skill
        variables = normalized_inputs.get("variables")
        equations = normalized_inputs.get("equations")
        x0 = normalized_inputs.get("x0")
        if not isinstance(variables, list) or not variables:
            return [
                ValidationOutcome(
                    layer=self.layer, severity=Severity.ERROR, messages=["variables required"]
                )
            ]
        if not isinstance(equations, list) or len(equations) != len(variables):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["equations length must equal variables"],
                )
            ]
        if not isinstance(x0, list) or len(x0) != len(variables):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["x0 length must equal variables"],
                )
            ]
        return []
