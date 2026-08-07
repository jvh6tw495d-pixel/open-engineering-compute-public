from __future__ import annotations

from typing import Any, ClassVar

from oec.ops.models import validate_ops
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class InfeasibilityExplainValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        ops = normalized_inputs.get("ops")
        if not isinstance(ops, dict):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["ops must be a mapping"],
                )
            ]
        try:
            problem = validate_ops(ops)
        except Exception as exc:  # noqa: BLE001 — surface as one error
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=[f"ops failed validation: {exc}"],
                )
            ]
        if problem.problem_class != "lp":
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["ops.problem_class must be 'lp' for infeasibility_explain"],
                )
            ]
        return []