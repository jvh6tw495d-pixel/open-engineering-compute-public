from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pymoo")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_runs_sphere() -> None:
    out = implementation.execute(
        {
            "variables": [
                {"name": "x1", "lower": -1.5, "upper": 1.5},
                {"name": "x2", "lower": -1.5, "upper": 1.5},
            ],
            "built_in": "sphere",
            "generations": 15,
            "population": 16,
            "seed": 1,
        }
    )
    assert out["result"]["backend"] == "pymoo"
    assert out["result"]["algorithm"] == "cma_es"
