"""Golden / smoke tests for neural.mlp.regressor (requires torch)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")

from oec.testing import load_skill_module  # noqa: E402

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

pytestmark = pytest.mark.neural


def test_linear_toy_overfits_reasonably() -> None:
    # y = 2x + 1
    x = [[float(i)] for i in range(12)]
    y = [2.0 * i + 1.0 for i in range(12)]
    out = implementation.execute(
        {
            "x": x,
            "y": y,
            "hidden_dims": [32, 16],
            "epochs": 150,
            "lr": 0.05,
            "val_fraction": 0.0,
            "seed": 0,
            "device": "cpu",
            "normalize_x": True,
        }
    )
    assert out["diagnostics"]["backend"] == "torch"
    assert "checkpoint" in out["result"]
    r2 = out["result"]["train_metrics"]["r_squared"]
    assert r2 > 0.9, r2
