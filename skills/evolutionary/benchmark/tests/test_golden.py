"""Benchmark harness smoke (requires pymoo)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pymoo")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_single_mode_table() -> None:
    out = implementation.execute(
        {
            "mode": "single",
            "variables": [
                {"name": "x1", "lower": -1.5, "upper": 1.5},
                {"name": "x2", "lower": -1.5, "upper": 1.5},
            ],
            "built_in": "sphere",
            "algorithms": ["differential_evolution", "pso"],
            "generations": 10,
            "population": 12,
            "seeds": [0, 1],
        }
    )
    assert out["result"]["mode"] == "single"
    assert len(out["result"]["rows"]) == 4  # 2 algos × 2 seeds
    assert "best_mean_algorithm" in out["result"]["summary"]


def test_multi_mode_table() -> None:
    vars_ = [{"name": f"x{i}", "lower": 0.0, "upper": 1.0} for i in range(4)]
    out = implementation.execute(
        {
            "mode": "multi",
            "variables": vars_,
            "multi_built_in": "zdt1",
            "multi_algorithms": ["nsga2", "nsga3"],
            "generations": 8,
            "population": 20,
            "seeds": [0],
        }
    )
    assert out["result"]["mode"] == "multi"
    assert len(out["result"]["rows"]) == 2
