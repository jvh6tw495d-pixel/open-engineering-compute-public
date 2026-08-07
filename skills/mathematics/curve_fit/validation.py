"""Skill-specific validation for mathematics.curve_fit (plan section 8).

JSON Schema (``input.schema.json``) already covers types, array shapes,
and ``max_iterations`` positivity; this module checks what JSON Schema
cannot express cleanly — cross-field length agreement between
``x``/``y``/``parameter_names``/``initial_guess``/``bounds``, whether
there are enough data points to fit the requested parameters, and
whether ``model`` actually parses against ``x`` plus the declared
parameter names.
"""

from __future__ import annotations

from typing import Any, ClassVar

from oec.kernel.numerics.expressions import ExpressionError, compile_expression_vector
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"
_INDEPENDENT_VARIABLE = "x"


class CurveFitValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        outcomes: list[ValidationOutcome] = []

        parameter_names = normalized_inputs.get("parameter_names")
        if not isinstance(parameter_names, list) or not parameter_names:
            # Missing/empty 'parameter_names' is already an INVALID at the
            # schema layer -- nothing further to check without a parameter
            # set to validate the model expression and lengths against.
            return outcomes

        if len(set(parameter_names)) != len(parameter_names):
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[f"'parameter_names' contains duplicates: {parameter_names}"],
                )
            )
        if _INDEPENDENT_VARIABLE in parameter_names:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        f"'parameter_names' must not include {_INDEPENDENT_VARIABLE!r} "
                        "(reserved for the independent variable)"
                    ],
                )
            )

        x = normalized_inputs.get("x")
        y = normalized_inputs.get("y")
        if isinstance(x, list) and isinstance(y, list) and len(x) != len(y):
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[f"'x' has {len(x)} entries but 'y' has {len(y)}"],
                )
            )
        if isinstance(x, list) and len(x) < len(parameter_names):
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        f"{len(x)} data point(s) is not enough to fit "
                        f"{len(parameter_names)} parameter(s)"
                    ],
                )
            )

        initial_guess = normalized_inputs.get("initial_guess")
        if isinstance(initial_guess, list) and len(initial_guess) != len(parameter_names):
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        f"'initial_guess' has {len(initial_guess)} entries but "
                        f"'parameter_names' has {len(parameter_names)}"
                    ],
                )
            )

        bounds = normalized_inputs.get("bounds")
        if isinstance(bounds, list):
            if len(bounds) != len(parameter_names):
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.ERROR,
                        messages=[
                            f"'bounds' has {len(bounds)} entries but "
                            f"'parameter_names' has {len(parameter_names)}"
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

        model = normalized_inputs.get("model")
        if isinstance(model, str):
            try:
                compile_expression_vector(model, symbols=(_INDEPENDENT_VARIABLE, *parameter_names))
            except ExpressionError as exc:
                outcomes.append(
                    ValidationOutcome(layer=_LAYER, severity=Severity.ERROR, messages=[exc.message])
                )

        return outcomes
