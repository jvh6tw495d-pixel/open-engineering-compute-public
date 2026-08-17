from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class VisionTransferValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        examples = normalized_inputs.get("examples")
        n_classes = int(normalized_inputs.get("n_classes", 0) or 0)
        if not isinstance(examples, list) or len(examples) < 2:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["examples must be a list of at least 2 labeled images"],
                )
            ]
        if n_classes < 2:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["n_classes must be >= 2"],
                )
            ]
        return []
