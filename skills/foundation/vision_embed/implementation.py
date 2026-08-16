"""foundation.vision_embed — closed CLIP-family image embeddings (S5 VLM MVP)."""

from __future__ import annotations

from typing import Any

from oec.foundation.contracts import FoundationModelSpec, VisionEmbeddingSpec, VisionImageInput
from oec.foundation.errors import (
    FoundationError,
    InvalidImageSourceError,
    ModelRevisionRequiredError,
    PillowNotAvailableError,
    TransformersNotAvailableError,
    UnsupportedVisionModelError,
)
from oec.foundation.runtime import vision_embed

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
    spec = VisionEmbeddingSpec(
        images=[_image_input(entry) for entry in inputs["images"]],
        model=model,
        dim=int(inputs.get("dim", 512)),
        normalize=bool(inputs.get("normalize", True)),
        seed=int(inputs.get("seed", 0)),
    )
    try:
        out = vision_embed(spec)
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
            "dim": out["dim"],
            "n": out["n"],
            "merit_owner": out.get("merit_owner"),
        },
    }
