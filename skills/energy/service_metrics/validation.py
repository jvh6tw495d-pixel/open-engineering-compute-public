"""Skill-package validation hook (contract completeness).

No extra cross-field checks beyond JSON Schema for this skill; pipeline
schema/dimensional layers remain authoritative.
"""

from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import ValidationOutcome


class PackageValidator:
    """No-op package validator (schema layer covers the contract)."""

    layer: ClassVar[str] = "physical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill, normalized_inputs
        return []
