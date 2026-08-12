"""Mathematical validation for mathematics.jacobian."""

from __future__ import annotations

from typing import Any, ClassVar

from oec.kernel.numerics.expressions import ExpressionError, compile_expression_vector
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class JacobianValidator:
    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        variables = normalized_inputs.get("variables")
        expressions = normalized_inputs.get("expressions")
        at = normalized_inputs.get("at")
        if not isinstance(variables, list) or not isinstance(expressions, list):
            return []
        if not isinstance(at, list):
            return []
        if len(variables) != len(at):
            return [
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[f"len(variables)={len(variables)} must equal len(at)={len(at)}"],
                )
            ]
        if len(set(variables)) != len(variables):
            return [
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["variables must be unique"],
                )
            ]
        symbols = tuple(str(v) for v in variables)
        for expr in expressions:
            if not isinstance(expr, str):
                continue
            try:
                compile_expression_vector(expr, symbols=symbols)
            except ExpressionError as exc:
                return [
                    ValidationOutcome(layer=_LAYER, severity=Severity.ERROR, messages=[exc.message])
                ]
        return []
