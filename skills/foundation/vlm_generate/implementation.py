"""foundation.vlm_generate — closed Vision2Seq vision-language generation (S5 VLM MVP)."""

from __future__ import annotations

from typing import Any

from oec.foundation.contracts import FoundationModelSpec, VisionImageInput, VLMGenerationSpec
from oec.foundation.errors import (
    FoundationError,
    InvalidImageSourceError,
    ModelRevisionRequiredError,
    PillowNotAvailableError,
    TransformersNotAvailableError,
    UnsupportedVisionModelError,
)
from oec.foundation.runtime import vlm_generate

_FAIL_CLOSED_ERRORS = (
    TransformersNotAvailableError,
    PillowNotAvailableError,
    InvalidImageSourceError,
    ModelRevisionRequiredError,
    UnsupportedVisionModelError,
)


def _image_input(entry: dict[str, Any]) -> VisionImageInput:
    kwargs: dict[str, Any] = {}
    if entry.get("image_base64") is not None:
        kwargs["image_base64"] = str(entry["image_base64"])
    if entry.get("image_path") is not None:
        kwargs["image_path"] = str(entry["image_path"])
    return VisionImageInput(**kwargs)


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    model = FoundationModelSpec(
        model_id=str(inputs["model_id"]),
        revision=str(inputs["revision"]) if inputs.get("revision") else None,
    )
    spec = VLMGenerationSpec(
        prompt=str(inputs["prompt"]),
        image=_image_input(inputs["image"]),
        model=model,
        max_new_tokens=int(inputs.get("max_new_tokens", 32)),
        temperature=float(inputs.get("temperature", 0.0)),
        seed=int(inputs.get("seed", 0)),
    )
    try:
        out = vlm_generate(spec)
    except _FAIL_CLOSED_ERRORS as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "transformers",
            },
        }
    except FoundationError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": False, "message": exc.message},
        }
    return {
        "result": out,
        "diagnostics": {
            "converged": True,
            "backend": out["backend"],
            "model_id": out["model_id"],
            "merit_owner": out.get("merit_owner"),
        },
    }
