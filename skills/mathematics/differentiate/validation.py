"""Skill-specific validation for mathematics.differentiate.

What JSON Schema (``input.schema.json``) already covers -- types,
``step > 0``, unknown properties -- is deliberately not repeated here.
This module only checks what JSON Schema cannot express: whether
``expression`` actually parses under the restricted-AST grammar.
"""

from __future__ import annotations

from typing import Any, ClassVar

from oec.kernel.numerics.expressions import ExpressionError, compile_expression
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class DifferentiateValidator:
    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        expression = normalized_inputs.get("expression")
        if not isinstance(expression, str):
            return []

        try:
            compile_expression(expression)
        except ExpressionError as exc:
            return [
                ValidationOutcome(layer=_LAYER, severity=Severity.ERROR, messages=[exc.message])
            ]
        return []
