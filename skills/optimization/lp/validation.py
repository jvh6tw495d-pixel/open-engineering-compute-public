"""Validation for optimization.lp — OPS must be class lp."""

from __future__ import annotations

from typing import Any, ClassVar

from oec.ops.models import validate_ops
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class LinearProgramValidator:
    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        outcomes: list[ValidationOutcome] = []
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
        if problem.problem_class != "lp":
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["optimization.lp requires ops.problem_class='lp'"],
                )
            )
        return outcomes
