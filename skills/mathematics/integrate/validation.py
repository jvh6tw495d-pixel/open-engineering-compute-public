"""Skill-specific validation for mathematics.integrate (plan section 14.1).

JSON Schema covers types, positivity of ``epsabs``/``epsrel``, and the
``method`` enum. This module only checks cross-field presence (exactly
one mode), expression parseability, bounds sanity, tabulated shape, and
that ``method: simpson`` is not requested with fewer than 3 points.
"""

from __future__ import annotations

from typing import Any, ClassVar

from oec.kernel.numerics.expressions import ExpressionError, compile_expression
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"
_SIMPSON_MIN_POINTS = 3


class IntegrateValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill  # interface contract; unused here
        outcomes: list[ValidationOutcome] = []

        expression = normalized_inputs.get("expression")
        bounds = normalized_inputs.get("bounds")
        x = normalized_inputs.get("x")
        y = normalized_inputs.get("y")
        method = normalized_inputs.get("method")

        has_function = expression is not None or bounds is not None
        has_tabulated = x is not None or y is not None

        if has_function and has_tabulated:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        "exactly one integration mode must be given: "
                        "('expression' + 'bounds') XOR ('x' + 'y'), not both"
                    ],
                )
            )
            return outcomes

        if not has_function and not has_tabulated:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        "exactly one integration mode must be given: "
                        "provide ('expression' + 'bounds') or ('x' + 'y')"
                    ],
                )
            )
            return outcomes

        if has_function:
            outcomes.extend(_validate_function_mode(expression, bounds, method))
        else:
            outcomes.extend(_validate_tabulated_mode(x, y, method))

        return outcomes


def _validate_function_mode(expression: Any, bounds: Any, method: Any) -> list[ValidationOutcome]:
    outcomes: list[ValidationOutcome] = []

    if not isinstance(expression, str):
        outcomes.append(
            ValidationOutcome(
                layer=_LAYER,
                severity=Severity.ERROR,
                messages=["function mode requires 'expression' (string)"],
            )
        )
    else:
        try:
            compile_expression(expression)
        except ExpressionError as exc:
            outcomes.append(
                ValidationOutcome(layer=_LAYER, severity=Severity.ERROR, messages=[exc.message])
            )

    if not isinstance(bounds, list) or len(bounds) != 2:
        outcomes.append(
            ValidationOutcome(
                layer=_LAYER,
                severity=Severity.ERROR,
                messages=["function mode requires 'bounds' as an array of exactly 2 numbers"],
            )
        )
    else:
        a, b = bounds
        if not (
            isinstance(a, int | float)
            and isinstance(b, int | float)
            and not isinstance(a, bool)
            and not isinstance(b, bool)
        ):
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["'bounds' elements must be numbers"],
                )
            )
        elif a == b:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=["'bounds' endpoints must be distinct (got equal endpoints)"],
                    details={"bounds": bounds},
                )
            )

    if method is not None:
        outcomes.append(
            ValidationOutcome(
                layer=_LAYER,
                severity=Severity.ERROR,
                messages=[
                    f"'method' is only accepted in tabulated mode "
                    f"(got method={method!r} with function-mode inputs)"
                ],
            )
        )

    return outcomes


def _validate_tabulated_mode(x: Any, y: Any, method: Any) -> list[ValidationOutcome]:
    outcomes: list[ValidationOutcome] = []

    if not isinstance(x, list) or not isinstance(y, list):
        outcomes.append(
            ValidationOutcome(
                layer=_LAYER,
                severity=Severity.ERROR,
                messages=["tabulated mode requires both 'x' and 'y' arrays"],
            )
        )
        return outcomes

    if len(x) != len(y):
        outcomes.append(
            ValidationOutcome(
                layer=_LAYER,
                severity=Severity.ERROR,
                messages=[
                    f"'x' and 'y' must have the same length (got len(x)={len(x)}, len(y)={len(y)})"
                ],
                details={"len_x": len(x), "len_y": len(y)},
            )
        )

    if len(x) < 2:
        outcomes.append(
            ValidationOutcome(
                layer=_LAYER,
                severity=Severity.ERROR,
                messages=[f"tabulated mode requires at least 2 sample points (got {len(x)})"],
            )
        )

    if not _is_strictly_increasing(x):
        outcomes.append(
            ValidationOutcome(
                layer=_LAYER,
                severity=Severity.ERROR,
                messages=["'x' must be strictly increasing (no duplicates, no inversions)"],
                details={"x": x},
            )
        )

    if method == "simpson" and len(x) < _SIMPSON_MIN_POINTS:
        outcomes.append(
            ValidationOutcome(
                layer=_LAYER,
                severity=Severity.ERROR,
                messages=[
                    f"method='simpson' requires at least {_SIMPSON_MIN_POINTS} sample "
                    f"points (got {len(x)}); use method='trapezoid' or omit method"
                ],
                details={"n_points": len(x), "minimum": _SIMPSON_MIN_POINTS},
            )
        )

    return outcomes


def _is_strictly_increasing(values: list[Any]) -> bool:
    if len(values) < 2:
        return True
    for left, right in zip(values, values[1:], strict=False):
        if not (
            isinstance(left, int | float)
            and isinstance(right, int | float)
            and not isinstance(left, bool)
            and not isinstance(right, bool)
        ):
            return False
        if not (left < right):
            return False
    return True
