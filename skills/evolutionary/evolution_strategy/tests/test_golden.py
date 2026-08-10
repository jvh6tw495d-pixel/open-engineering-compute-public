from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("deap")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_es_sphere() -> None:
    out = implementation.execute(
        {
            "built_in": "sphere",
            "n_var": 2,
            "population": 20,
            "generations": 20,
            "seed": 0,
        }
    )
    assert out["result"]["backend"] == "deap"
    assert out["result"]["best_objective"] < 5.0
