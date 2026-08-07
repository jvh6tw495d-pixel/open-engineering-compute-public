"""Reusable mathematical-domain checks for skill-specific validation (plan section 12.3).

These are pure helpers, not pipeline-wired :class:`~oec.validation.base.InputValidator`
classes. A future skill's own ``validation.py`` (Sprint 04+) calls them for
cross-field and structural rules that JSON Schema does not express well —
root-finding brackets, matrix shape, non-zero denominators, etc.

Range/positivity constraints that *can* be expressed with JSON Schema
(``minimum``, ``maximum``, ``exclusiveMinimum``) belong in
:class:`~oec.validation.schema.SchemaValidator`, not here.
"""

from __future__ import annotations

from oec.validation.base import Severity, ValidationOutcome

LAYER = "mathematical"


def require_nonzero(field: str, value: float) -> ValidationOutcome:
    """Require ``value`` to be non-zero (e.g. a denominator)."""
    if value == 0.0:
        return ValidationOutcome(
            layer=LAYER,
            severity=Severity.ERROR,
            messages=[f"field {field!r} must be non-zero"],
            details={"field": field, "value": value},
        )
    return ValidationOutcome(layer=LAYER, severity=Severity.OK)


def require_in_range(
    field: str,
    value: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> ValidationOutcome:
    """Require ``value`` to lie within an optional closed ``[minimum, maximum]`` interval."""
    if minimum is not None and value < minimum:
        return ValidationOutcome(
            layer=LAYER,
            severity=Severity.ERROR,
            messages=[f"field {field!r} must be >= {minimum}, got {value}"],
            details={"field": field, "value": value, "minimum": minimum, "maximum": maximum},
        )
    if maximum is not None and value > maximum:
        return ValidationOutcome(
            layer=LAYER,
            severity=Severity.ERROR,
            messages=[f"field {field!r} must be <= {maximum}, got {value}"],
            details={"field": field, "value": value, "minimum": minimum, "maximum": maximum},
        )
    return ValidationOutcome(layer=LAYER, severity=Severity.OK)


def require_bracket(field_a: str, f_a: float, field_b: str, f_b: float) -> ValidationOutcome:
    """Require opposite signs for a root-finding bracket (``f_a * f_b < 0``).

    A product of zero means at least one endpoint is already a root or is
    flat; product positive means no sign change — both are invalid brackets.
    """
    if f_a * f_b >= 0.0:
        return ValidationOutcome(
            layer=LAYER,
            severity=Severity.ERROR,
            messages=[
                f"fields {field_a!r} and {field_b!r} do not form a valid root-finding "
                f"bracket (f({field_a})={f_a}, f({field_b})={f_b}; need opposite signs)"
            ],
            details={"field_a": field_a, "f_a": f_a, "field_b": field_b, "f_b": f_b},
        )
    return ValidationOutcome(layer=LAYER, severity=Severity.OK)


def require_square_matrix(field: str, matrix: list[list[float]]) -> ValidationOutcome:
    """Require ``matrix`` to be a square list-of-lists (n rows, each of length n)."""
    n_rows = len(matrix)
    for row_index, row in enumerate(matrix):
        if not isinstance(row, list):
            return ValidationOutcome(
                layer=LAYER,
                severity=Severity.ERROR,
                messages=[f"field {field!r}: row {row_index} is not a list"],
                details={"field": field, "row_index": row_index},
            )
        if len(row) != n_rows:
            return ValidationOutcome(
                layer=LAYER,
                severity=Severity.ERROR,
                messages=[
                    f"field {field!r} must be a square matrix: "
                    f"{n_rows} rows but row {row_index} has length {len(row)}"
                ],
                details={
                    "field": field,
                    "n_rows": n_rows,
                    "row_index": row_index,
                    "row_length": len(row),
                },
            )
    return ValidationOutcome(layer=LAYER, severity=Severity.OK)
