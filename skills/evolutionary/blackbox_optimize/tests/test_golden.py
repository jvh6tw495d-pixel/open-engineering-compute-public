from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("nevergrad")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_blackbox_sphere() -> None:
    out = implementation.execute(
        {
            "built_in": "sphere",
            "n_var": 2,
            "budget": 80,
            "optimizer": "OnePlusOne",
            "seed": 0,
        }
    )
    assert out["result"]["backend"] == "nevergrad"
    assert out["result"]["best_objective"] < 10.0
