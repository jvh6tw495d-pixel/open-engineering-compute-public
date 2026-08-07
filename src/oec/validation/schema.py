"""JSON Schema validation of skill inputs (plan section 12.1).

The first pre-execution layer: check that normalized inputs match the
skill's declared ``input_schema`` before any dimensional or domain
checks run. Errors here mean the caller sent a malformed request, so the
implementation never executes (ADR 0007 → ``INVALID``).
"""

from __future__ import annotations

from typing import Any, ClassVar

from jsonschema import Draft202012Validator

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class SchemaValidator:
    """Validate ``normalized_inputs`` against a skill's parsed JSON Schema."""

    layer: ClassVar[str] = "schema"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        validator = Draft202012Validator(skill.input_schema)
        outcomes: list[ValidationOutcome] = []
        for error in validator.iter_errors(normalized_inputs):
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
