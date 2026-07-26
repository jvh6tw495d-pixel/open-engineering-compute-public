"""Validation for optimization.milp."""

from __future__ import annotations

from typing import Any, ClassVar

from oec.ops.models import validate_ops
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class MixedIntegerLinearProgramValidator:
    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        ops_doc = normalized_inputs.get("ops")
        if not isinstance(ops_doc, dict):
            return [
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["'ops' must be an object (OPS v0.1 document)"],
                )
            ]
        try:
            problem = validate_ops(ops_doc)
        except Exception as exc:
            return [
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[str(exc)],
                )
            ]
        if problem.problem_class != "milp":
            return [
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["optimization.milp requires ops.problem_class='milp'"],
                )
            ]
        return []
