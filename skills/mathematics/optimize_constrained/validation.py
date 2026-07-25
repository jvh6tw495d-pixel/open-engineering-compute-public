"""Skill-specific validation for mathematics.optimize_constrained (plan section 8).

JSON Schema (``input.schema.json``) already covers types, array shapes,
and ``tolerance``/``max_iterations`` positivity; this module checks what
JSON Schema cannot express cleanly — cross-field length agreement
between ``variables``/``x0``/``bounds``, bound-interval well-formedness,
and whether ``expression``/``constraints[].expression`` actually parse
against the declared variable names.
"""

from __future__ import annotations

from typing import Any, ClassVar

from oec.kernel.numerics.expressions import ExpressionError, compile_expression_vector
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class OptimizeConstrainedValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        outcomes: list[ValidationOutcome] = []

        variables = normalized_inputs.get("variables")
        if not isinstance(variables, list) or not variables:
            # Missing/empty 'variables' is already an INVALID at the schema
            # layer (required, minItems: 1) -- nothing further to check here
            # without a variable set to validate expressions against.
            return outcomes

        if len(set(variables)) != len(variables):
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[f"'variables' contains duplicate names: {variables}"],
                )
            )

        symbols = tuple(variables)

        x0 = normalized_inputs.get("x0")
        if isinstance(x0, list) and len(x0) != len(variables):
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[f"'x0' has {len(x0)} entries but 'variables' has {len(variables)}"],
                )
            )

        bounds = normalized_inputs.get("bounds")
        if isinstance(bounds, list):
            if len(bounds) != len(variables):
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=[
                            f"'bounds' has {len(bounds)} entries but "
                            f"'variables' has {len(variables)}"
                        ],
                    )
                )
            for pair in bounds:
                if isinstance(pair, list) and len(pair) == 2:
                    lo, hi = pair
                    if lo is not None and hi is not None and lo >= hi:
                        outcomes.append(
                            ValidationOutcome(
                                layer=_LAYER,
                                severity=Severity.ERROR,
                                messages=[
                                    f"bounds pair [{lo}, {hi}] is not a valid interval "
                                    "(lo must be < hi)"
                                ],
                                details={"bounds": pair},
                            )
                        )

        expression = normalized_inputs.get("expression")
        if isinstance(expression, str):
            try:
                compile_expression_vector(expression, symbols=symbols)
            except ExpressionError as exc:
                outcomes.append(
                    ValidationOutcome(layer=_LAYER, severity=Severity.ERROR, messages=[exc.message])
                )

        constraints = normalized_inputs.get("constraints")
        if isinstance(constraints, list):
            for index, constraint in enumerate(constraints):
                if not isinstance(constraint, dict):
                    continue
                constraint_expression = constraint.get("expression")
                if isinstance(constraint_expression, str):
                    try:
                        compile_expression_vector(constraint_expression, symbols=symbols)
                    except ExpressionError as exc:
                        outcomes.append(
                            ValidationOutcome(
                                layer=_LAYER,
                                severity=Severity.ERROR,
                                messages=[f"constraints[{index}].expression: {exc.message}"],
                            )
                        )

        return outcomes
