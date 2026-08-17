"""Vision transfer: frozen-feature MLP vs fine-tuned head."""

from __future__ import annotations

from pathlib import Path

import pytest

from oec.experiment.cross_domain import build_vision_head_vs_backbone_experiment
from oec.neural.vision import (
    VisionBackboneName,
    VisionBackboneWeights,
    VisionLabeledImage,
    VisionTransferMode,
    VisionTransferSpec,
)

pytest.importorskip("torch")
pytest.importorskip("torchvision")
pytest.importorskip("PIL")


def _png(path: Path, color: tuple[int, int, int]) -> None:
    from PIL import Image

    Image.new("RGB", (32, 32), color).save(path)


def _examples(tmp_path: Path) -> list[dict[str, object]]:
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    c = tmp_path / "c.png"
    d = tmp_path / "d.png"
    _png(a, (200, 30, 30))
    _png(b, (30, 30, 200))
    _png(c, (180, 40, 40))
    _png(d, (40, 40, 180))
    return [
        {"path": str(a), "label": 0},
        {"path": str(b), "label": 1},
        {"path": str(c), "label": 0},
        {"path": str(d), "label": 1},
    ]


def test_clip_requires_revision() -> None:
    with pytest.raises(ValueError, match="clip_revision"):
        VisionTransferSpec(
            examples=(
                VisionLabeledImage(path="a.png", label=0),
                VisionLabeledImage(path="b.png", label=1),
            ),
            n_classes=2,
            backbone=VisionBackboneName.CLIP,
        )


def test_builder_compares_two_modes(tmp_path: Path) -> None:
    spec = build_vision_head_vs_backbone_experiment(
        examples=_examples(tmp_path),
        n_classes=2,
        backbone_weights="none",
        epochs=2,
    )
    assert [step.step_id for step in spec.steps] == ["frozen_head", "finetune_head"]
    assert spec.steps[0].skill_id == "neural.vision.transfer"
    assert spec.steps[0].inputs["mode"] == "frozen_features"
    assert spec.steps[1].inputs["mode"] == "finetune_head"


def test_frozen_features_trains_mlp_head(tmp_path: Path) -> None:
    from oec.kernel.neural.vision_transfer import run_vision_transfer

    rows = _examples(tmp_path)
    spec = VisionTransferSpec(
        examples=tuple(
            VisionLabeledImage(path=str(r["path"]), label=int(r["label"])) for r in rows
        ),
        n_classes=2,
        backbone=VisionBackboneName.RESNET18,
        mode=VisionTransferMode.FROZEN_FEATURES,
        backbone_weights=VisionBackboneWeights.NONE,
        hidden_dims=(16,),
        epochs=3,
        val_fraction=0.25,
        seed=0,
        device="cpu",
    )
    out = run_vision_transfer(spec)
    assert out["mode"] == "frozen_features"
    assert out["backend"] == "torchvision.resnet18"
    assert out["feature_dim"] == 512
    assert out["checkpoint"] is not None
    assert "accuracy" in out["train_metrics"] or "mae" in out["train_metrics"]


def test_finetune_head_reports_trainable_params(tmp_path: Path) -> None:
    from oec.kernel.neural.vision_transfer import run_vision_transfer

    rows = _examples(tmp_path)
    spec = VisionTransferSpec(
        examples=tuple(
            VisionLabeledImage(path=str(r["path"]), label=int(r["label"])) for r in rows
        ),
        n_classes=2,
        mode=VisionTransferMode.FINETUNE_HEAD,
        backbone_weights=VisionBackboneWeights.NONE,
        hidden_dims=(16,),
        epochs=2,
        val_fraction=0.0,
        seed=0,
        device="cpu",
    )
    out = run_vision_transfer(spec)
    assert out["mode"] == "finetune_head"
    assert int(out["n_params"] or 0) > 0
    assert out["train_metrics"]["accuracy"] >= 0.0
