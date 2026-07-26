from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class OdeValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(self, skill: LoadedSkill, normalized_inputs: dict[str, Any]):
        del skill
        state = normalized_inputs.get("state_names")
        dydt = normalized_inputs.get("dydt_expressions")
        y0 = normalized_inputs.get("y0")
        t_span = normalized_inputs.get("t_span")
        if not isinstance(state, list) or not state:
            return [
                ValidationOutcome(
                    layer=self.layer, severity=Severity.ERROR, messages=["state_names required"]
                )
            ]
        if not isinstance(dydt, list) or len(dydt) != len(state):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["dydt_expressions length must match state"],
                )
            ]
        if not isinstance(y0, list) or len(y0) != len(state):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["y0 length must match state"],
                )
            ]
        if not isinstance(t_span, list) or len(t_span) != 2:
            return [
                ValidationOutcome(
                    layer=self.layer, severity=Severity.ERROR, messages=["t_span must be [t0, tf]"]
                )
            ]
        return []
