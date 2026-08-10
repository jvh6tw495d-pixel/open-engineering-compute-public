from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.neural


def test_transformer_runs() -> None:
    x = []
    y = []
    for i in range(20):
        seq = [[float(i + t) * 0.05] for t in range(5)]
        x.append(seq)
        y.append(float(i) * 0.05)
    out = implementation.execute(
        {
            "task": "classification",
            "n_classes": 2,
            "x": x,
            "y": y,
            "epochs": 15,
            "d_model": 16,
            "n_heads": 2,
            "n_layers": 1,
            "ff_dim": 32,
            "seed": 0,
            "device": "cpu",
        }
    )
    assert out["result"]["backend"] == "torch"
