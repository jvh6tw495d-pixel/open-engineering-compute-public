"""Evaluate skill smoke (requires torch)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")

from oec.testing import load_skill_module  # noqa: E402

_REG = Path(__file__).resolve().parents[2] / "mlp_regressor"
_EV = Path(__file__).resolve().parent.parent
train_impl = load_skill_module(_REG, "implementation")
eval_impl = load_skill_module(_EV, "implementation")
pytestmark = pytest.mark.neural


def test_evaluate_after_train() -> None:
    x = [[float(i)] for i in range(10)]
    y = [2.0 * i + 1.0 for i in range(10)]
    trained = train_impl.execute(
        {
            "x": x,
            "y": y,
            "hidden_dims": [16],
            "epochs": 50,
            "lr": 0.05,
            "val_fraction": 0.0,
            "seed": 2,
            "device": "cpu",
        }
    )
    out = eval_impl.execute(
        {
            "x": x,
            "y": y,
            "checkpoint": trained["result"]["checkpoint"],
            "normalize": trained["result"].get("normalize"),
            "task": "regression",
        }
    )
    assert out["result"]["metrics"]["r_squared"] > 0.8
