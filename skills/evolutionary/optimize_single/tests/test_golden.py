"""Evolutionary optimize_single smoke (requires pymoo)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pymoo")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_sphere_de_finds_near_origin() -> None:
    out = implementation.execute(
        {
            "variables": [
                {"name": "x1", "lower": -2.0, "upper": 2.0},
                {"name": "x2", "lower": -2.0, "upper": 2.0},
            ],
            "built_in": "sphere",
            "algorithm": "differential_evolution",
            "generations": 25,
            "population": 20,
            "seed": 0,
        }
    )
    assert out["result"]["backend"] == "pymoo"
    assert out["result"]["best_objective"] < 0.1
