"""Validation for foundation.vlm_generate."""

from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class Validator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        messages: list[str] = []

        prompt = normalized_inputs.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            messages.append("prompt must be a non-empty string")

        image = normalized_inputs.get("image")
        if not isinstance(image, dict):
            messages.append("image must be an object")
        else:
            has_b64 = bool(image.get("image_base64"))
            has_path = bool(image.get("image_path"))
            if has_b64 == has_path:
                messages.append("image requires exactly one of image_base64 or image_path")

        model_id = normalized_inputs.get("model_id")
        if not isinstance(model_id, str) or not model_id.strip():
            messages.append("model_id must be a non-empty string")

        if messages:
            return [ValidationOutcome(layer=self.layer, severity=Severity.ERROR, messages=messages)]
        return []
