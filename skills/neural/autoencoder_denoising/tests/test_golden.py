from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.neural


def test_reconstructs() -> None:
    import numpy as np

    rng = np.random.default_rng(0)
    x = (rng.normal(size=(40, 6))).tolist()
    out = implementation.execute(
        {"x": x, "epochs": 25, "latent_dim": 4, "seed": 0, "device": "cpu"}
    )
    assert out["result"]["backend"] == "torch"
    assert out["result"]["train_metrics"]["mse"] < 2.0
