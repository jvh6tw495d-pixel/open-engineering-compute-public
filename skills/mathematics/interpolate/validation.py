"""Skill-specific validation for mathematics.interpolate (plan section 14.1).

JSON Schema (``input.schema.json``) already covers types, required keys,
``method`` enum, and minimum array lengths. This module only checks what
JSON Schema cannot express cleanly: equal lengths, strictly increasing
``x``, cubic-spline sample-count floor, and out-of-range query points
(extrapolation → WARNING, not ERROR).
"""

from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_LAYER = "mathematical"
_CUBIC_SPLINE_MIN_POINTS = 4


class InterpolateValidator:
    """Cross-field and domain checks JSON Schema alone can't express."""

    layer: ClassVar[str] = _LAYER

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill  # interface contract; unused here
        outcomes: list[ValidationOutcome] = []

        x = normalized_inputs.get("x")
        y = normalized_inputs.get("y")
        query_points = normalized_inputs.get("query_points")
        method = normalized_inputs.get("method")

        if not isinstance(x, list) or not isinstance(y, list):
            return outcomes

        if len(x) != len(y):
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        f"'x' and 'y' must have the same length "
                        f"(got len(x)={len(x)}, len(y)={len(y)})"
                    ],
                    details={"len_x": len(x), "len_y": len(y)},
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

        if method == "cubic_spline" and len(x) < _CUBIC_SPLINE_MIN_POINTS:
            outcomes.append(
                ValidationOutcome(
                    layer=_LAYER,
                    severity=Severity.ERROR,
                    messages=[
                        f"method='cubic_spline' requires at least "
                        f"{_CUBIC_SPLINE_MIN_POINTS} sample points "
                        f"(got {len(x)}); use 'linear' or 'pchip' for fewer points"
                    ],
                    details={"n_samples": len(x), "minimum": _CUBIC_SPLINE_MIN_POINTS},
                )
            )

        if (
            isinstance(query_points, list)
            and x
            and all(isinstance(v, int | float) and not isinstance(v, bool) for v in x)
        ):
            x_min = min(x)
            x_max = max(x)
            outside = [
                q
                for q in query_points
                if isinstance(q, int | float)
                and not isinstance(q, bool)
                and (q < x_min or q > x_max)
            ]
            if outside:
                outcomes.append(
                    ValidationOutcome(
                        layer=_LAYER,
                        severity=Severity.WARNING,
                        messages=[
                            "one or more query_points lie outside [min(x), max(x)] "
                            "(extrapolation is allowed but less reliable than "
                            "interpolation within the sample range)"
                        ],
                        details={
                            "x_min": x_min,
                            "x_max": x_max,
                            "out_of_range_query_points": outside,
                        },
                    )
                )

        return outcomes


def _is_strictly_increasing(values: list[Any]) -> bool:
    """True iff every adjacent pair satisfies v[i] < v[i+1]."""
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
