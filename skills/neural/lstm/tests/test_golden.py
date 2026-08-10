from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.neural


def test_sequence_runs() -> None:
    # y = mean of sequence feature 0
    x = []
    y = []
    for i in range(24):
        seq = [[float(i + t) * 0.1, 0.5] for t in range(6)]
        x.append(seq)
        y.append(sum(s[0] for s in seq) / 6.0)
    out = implementation.execute(
        {
            "x": x,
            "y": y,
            "epochs": 20,
            "hidden": 16,
            "seed": 0,
            "device": "cpu",
            "task": "regression",
        }
    )
    assert out["result"]["backend"] == "torch"
    assert "checkpoint" in out["result"]
