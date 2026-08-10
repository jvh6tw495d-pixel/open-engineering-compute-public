from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.neural


def test_smoke() -> None:
    x = [[float(i)] for i in range(16)]
    y = [2.0 * i + 1.0 for i in range(16)]
    out = implementation.execute(
        {
            "x": x,
            "y": y,
            "seed": 0,
            "max_evaluations": 4,
            "inner_epochs": 8,
            "epochs": 15,
            "device": "cpu",
        }
    )
    assert "result" in out
    assert out["diagnostics"].get("backend") in (
        "torch",
        "hybrid",
        "neuroevolution",
        "benchmark",
    )
