"""Post-execution invariant checks on a skill's result (plan section 12.6).

Two structural guarantees every result must satisfy:

1. No numeric leaf is ``NaN`` or ``±Infinity`` (a solver that returned
   garbage should never look "valid").
2. If the skill declared a non-empty ``output_schema``, the result must
   conform to it (shape invariant).

Errors here map to ``INVALID`` under ADR 0007 even though the
implementation did produce a result.
"""

from __future__ import annotations

import math
from typing import Any, ClassVar

from jsonschema import Draft202012Validator

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class InvariantValidator:
    """Check result finiteness and optional output-schema shape."""

    layer: ClassVar[str] = "invariants"

    def validate(
        self,
        skill: LoadedSkill,
        normalized_inputs: dict[str, Any],
        result: dict[str, Any],
        diagnostics: dict[str, Any],
    ) -> list[ValidationOutcome]:
        del normalized_inputs, diagnostics  # interface contract; unused here
        outcomes: list[ValidationOutcome] = []

        for path in _non_finite_paths(result, path="result"):
            outcomes.append(
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=[f"non-finite numeric value at {path}"],
                    details={"path": path},
                )
            )

        if skill.output_schema:
            validator = Draft202012Validator(skill.output_schema)
            for error in validator.iter_errors(result):
                details: dict[str, Any] = {}
                json_path = getattr(error, "json_path", None)
                if json_path is not None:
                    details["json_path"] = json_path
                outcomes.append(
                    ValidationOutcome(
                        layer=self.layer,
                        severity=Severity.ERROR,
                        messages=[error.message],
                        details=details,
                    )
                )

        return outcomes


def _non_finite_paths(node: Any, *, path: str) -> list[str]:
    """Recursively collect paths to NaN/Infinity leaves in dicts and lists."""
    found: list[str] = []
    if isinstance(node, float) and (math.isnan(node) or math.isinf(node)):
        found.append(path)
    elif isinstance(node, dict):
        for key, value in node.items():
            found.extend(_non_finite_paths(value, path=f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_non_finite_paths(value, path=f"{path}[{index}]"))
    return found
