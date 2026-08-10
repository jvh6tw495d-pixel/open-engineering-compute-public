"""Predict skill smoke (requires torch)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")

from oec.testing import load_skill_module  # noqa: E402

_REG = Path(__file__).resolve().parents[2] / "mlp_regressor"
_PRED = Path(__file__).resolve().parent.parent

train_impl = load_skill_module(_REG, "implementation")
pred_impl = load_skill_module(_PRED, "implementation")

pytestmark = pytest.mark.neural


def test_train_then_predict_shapes() -> None:
    x = [[float(i)] for i in range(10)]
    y = [2.0 * i + 1.0 for i in range(10)]
    trained = train_impl.execute(
        {
            "x": x,
            "y": y,
            "hidden_dims": [16],
            "epochs": 40,
            "lr": 0.05,
            "val_fraction": 0.0,
            "seed": 1,
            "device": "cpu",
        }
    )
    ckpt = trained["result"]["checkpoint"]
    norm = trained["result"].get("normalize")
    out = pred_impl.execute({"x": [[0.0], [1.0], [2.0]], "checkpoint": ckpt, "normalize": norm})
    assert len(out["result"]["predictions"]) == 3
