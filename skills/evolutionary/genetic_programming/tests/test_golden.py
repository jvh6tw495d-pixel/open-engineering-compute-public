from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("deap")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_gp_poly2_improves() -> None:
    out = implementation.execute(
        {
            "target": "poly2",
            "n_var": 1,
            "n_samples": 30,
            "population": 40,
            "generations": 12,
            "max_depth": 4,
            "seed": 0,
        }
    )
    assert out["result"]["backend"] == "deap"
    assert "best_tree_ir" in out["result"]
    assert out["result"]["best_mse"] < 1e5
