from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("neat")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_runs_xor() -> None:
    out = implementation.execute(
        {
            "fitness": "xor",
            "generations": 4,
            "population": 10,
            "seed": 1,
        }
    )
    result = out["result"]
    assert "error" not in result
    assert result["backend"] == "neat-python"
    assert result["algorithm"] == "neat"
    assert result["fitness"] == "xor"
    assert result["n_nodes"] >= 3
    assert result["genotype"]["n_inputs"] == 2
    assert result["genotype"]["n_outputs"] == 1
    assert isinstance(result["best_fitness"], float)
