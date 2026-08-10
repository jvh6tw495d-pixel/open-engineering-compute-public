from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")
pytest.importorskip("nevergrad")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = [pytest.mark.neural, pytest.mark.evolutionary]


def test_hyperparam_search() -> None:
    x = [[float(i)] for i in range(16)]
    y = [2.0 * i + 1.0 for i in range(16)]
    out = implementation.execute(
        {"x": x, "y": y, "budget": 3, "epochs": 12, "seed": 0, "device": "cpu"}
    )
    assert "best_config" in out["result"]
    assert out["result"]["n_trials"] >= 1
