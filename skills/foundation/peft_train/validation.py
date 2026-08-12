"""Validation for foundation.peft_train."""

from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome

_MODES = {"peft_lora", "peft_qlora", "full"}


class Validator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        messages: list[str] = []

        mode = normalized_inputs.get("mode", "peft_lora")
        if mode not in _MODES:
            messages.append(f"mode must be one of {sorted(_MODES)}")

        texts = normalized_inputs.get("texts")
        dataset_path = normalized_inputs.get("dataset_path")
        if bool(texts) == bool(dataset_path):
            messages.append("exactly one of texts or dataset_path must be provided")
        if texts is not None and not all(isinstance(t, str) and t.strip() for t in texts):
            messages.append("texts entries must be non-empty strings")

        if messages:
            return [ValidationOutcome(layer=self.layer, severity=Severity.ERROR, messages=messages)]
        return []
