"""Skill-specific validation for mathematics.solve_root (plan section 8).

This is the first real consumer of ``oec.validation.mathematical``'s
reusable helpers (built in Sprint 03 but never exercised by an actual
skill until now) and the template for how a skill's own ``validation.py``
implements :class:`oec.validation.base.InputValidator`.

What JSON Schema (``input.schema.json``, checked by
``oec.validation.schema.SchemaValidator``) already covers -- types,
``tolerance``/``max_iterations`` positivity, unknown properties -- is
deliberately not repeated here. This module only checks what JSON
Schema cannot express cleanly: cross-field presence rules and whether
the bracket actually brackets a sign change.
"""

from __future__ import annotations

from typing import Any, ClassVar

from oec.kernel.numerics.expressions import ExpressionError, compile_expression
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome
from oec.validation.mathematical import require_bracket

_LAYER = "mathematical"


class SolveRootValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        outcomes: list[ValidationOutcome] = []

        bracket = normalized_inputs.get("bracket")
        initial_guess = normalized_inputs.get("initial_guess")
        method = normalized_inputs.get("method")
        derivative = normalized_inputs.get("derivative")

        if bracket is None and initial_guess is None:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["either 'bracket' or 'initial_guess' must be provided"],
                )
            )

        if method == "newton" and derivative is None:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["method='newton' requires 'derivative'"],
                )
            )
        if method is not None and method != "newton" and derivative is not None:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        f"'derivative' is only accepted with method='newton', got {method!r}"
                    ],
                )
            )

        expression = normalized_inputs.get("expression")
        f = None
        if isinstance(expression, str):
            try:
                f = compile_expression(expression)
            except ExpressionError as exc:
                outcomes.append(
                    ValidationOutcome(layer=_LAYER, severity=Severity.ERROR, messages=[exc.message])
                )

        if isinstance(derivative, str):
            try:
                compile_expression(derivative)
            except ExpressionError as exc:
                outcomes.append(
                    ValidationOutcome(layer=_LAYER, severity=Severity.ERROR, messages=[exc.message])
                )

        if f is not None and isinstance(bracket, list) and len(bracket) == 2:
            a, b = bracket
            outcome = require_bracket("bracket[0]", f(a), "bracket[1]", f(b))
            if outcome.severity is not Severity.OK:
                outcomes.append(outcome)

        return outcomes
