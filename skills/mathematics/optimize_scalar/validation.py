"""Skill-specific validation for mathematics.optimize_scalar (plan section 8).

Mirrors ``mathematics.solve_root``'s ``SolveRootValidator`` (Sprint 04
template): JSON Schema (``input.schema.json``) already covers types and
``tolerance``/``max_iterations`` positivity; this module only checks
what JSON Schema cannot express cleanly — cross-field presence rules
between ``method`` and ``bounds``, interval well-formedness, and
whether ``expression`` actually parses.
"""

from __future__ import annotations

from typing import Any, ClassVar

from oec.kernel.numerics.expressions import ExpressionError, compile_expression
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"


class OptimizeScalarValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        outcomes: list[ValidationOutcome] = []

        method = normalized_inputs.get("method")
        bounds = normalized_inputs.get("bounds")

        if method == "bounded" and bounds is None:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["method='bounded' requires 'bounds'"],
                )
            )
        if method is not None and method != "bounded" and bounds is not None:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[f"'bounds' is only accepted with method='bounded', got {method!r}"],
                )
            )

        if isinstance(bounds, list) and len(bounds) == 2:
            lo, hi = bounds
            if lo >= hi:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=[
                            f"'bounds' [{lo}, {hi}] is not a valid interval (lo must be < hi)"
                        ],
                        details={"bounds": bounds},
                    )
                )

        expression = normalized_inputs.get("expression")
        if isinstance(expression, str):
            try:
                compile_expression(expression)
            except ExpressionError as exc:
                outcomes.append(
                    ValidationOutcome(layer=_LAYER, severity=Severity.ERROR, messages=[exc.message])
                )

        return outcomes
