"""neural.vision.transfer — backbone backend + OEC head."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.vision_transfer import run_vision_transfer
from oec.neural.vision import (
    VisionBackboneName,
    VisionBackboneWeights,
    VisionLabeledImage,
    VisionTransferMode,
    VisionTransferSpec,
)


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        spec = VisionTransferSpec(
            examples=tuple(
                VisionLabeledImage(path=str(row["path"]), label=int(row["label"]))
                for row in inputs["examples"]
            ),
            n_classes=int(inputs["n_classes"]),
            backbone=VisionBackboneName(inputs.get("backbone", "resnet18")),
            mode=VisionTransferMode(inputs.get("mode", "frozen_features")),
            backbone_weights=VisionBackboneWeights(inputs.get("backbone_weights", "imagenet")),
            clip_model_id=str(inputs.get("clip_model_id", "openai/clip-vit-base-patch32")),
            clip_revision=inputs.get("clip_revision"),
            hidden_dims=tuple(int(v) for v in inputs.get("hidden_dims", [64, 64])),
            epochs=int(inputs.get("epochs", 20)),
            batch_size=int(inputs.get("batch_size", 8)),
            lr=float(inputs.get("lr", 1e-3)),
            val_fraction=float(inputs.get("val_fraction", 0.25)),
            seed=int(inputs.get("seed", 0)),
            device=inputs.get("device", "cpu"),
        )
        payload = run_vision_transfer(spec)
    except (TorchNotAvailableError, ValueError) as exc:
        message = getattr(exc, "message", str(exc))
        return {
            "result": {"error": {"message": message}},
            "diagnostics": {"converged": False, "message": message, "backend": "vision"},
        }
    return {
        "result": payload,
        "diagnostics": {
            "converged": True,
            "backend": payload.get("backend"),
            "mode": payload.get("mode"),
            "train_accuracy": (payload.get("train_metrics") or {}).get("accuracy"),
            "n_params": payload.get("n_params"),
        },
    }
