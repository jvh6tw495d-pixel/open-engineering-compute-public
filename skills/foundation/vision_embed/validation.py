"""Validation for foundation.vision_embed."""

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

        images = normalized_inputs.get("images")
        if not isinstance(images, list) or not images:
            messages.append("images must be a non-empty list")
        else:
            for i, entry in enumerate(images):
                if not isinstance(entry, dict):
                    messages.append(f"images[{i}] must be an object")
                    continue
                has_b64 = bool(entry.get("image_base64"))
                has_path = bool(entry.get("image_path"))
                if has_b64 == has_path:
                    messages.append(
                        f"images[{i}] requires exactly one of image_base64 or image_path"
                    )

        model_id = normalized_inputs.get("model_id")
        if not isinstance(model_id, str) or not model_id.strip():
            messages.append("model_id must be a non-empty string")

        if messages:
            return [ValidationOutcome(layer=self.layer, severity=Severity.ERROR, messages=messages)]
        return []
