"""Classifier smoke (requires torch)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.neural


def test_binary_separable_runs() -> None:
    x = [[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]] * 3
    y = [0, 1, 1, 0] * 3
    out = implementation.execute(
        {
            "x": x,
            "y": y,
            "n_classes": 2,
            "hidden_dims": [16],
            "epochs": 40,
            "seed": 0,
            "device": "cpu",
            "val_fraction": 0.0,
        }
    )
    assert out["result"]["backend"] == "torch"
    assert "checkpoint" in out["result"]
