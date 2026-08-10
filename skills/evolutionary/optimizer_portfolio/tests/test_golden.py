from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("nevergrad")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_portfolio() -> None:
    out = implementation.execute(
        {
            "built_in": "sphere",
            "n_var": 2,
            "budget": 40,
            "optimizers": ["OnePlusOne", "RandomSearch"],
            "seed": 0,
        }
    )
    assert out["result"]["backend"] == "nevergrad"
    assert len(out["result"]["rows"]) == 2
    assert "best_optimizer" in out["result"]
