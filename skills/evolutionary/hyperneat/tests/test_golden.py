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
            "generations": 3,
            "population": 8,
            "seed": 1,
            "hidden_layers": 1,
            "hidden_width": 3,
        }
    )
    result = out["result"]
    assert "error" not in result
    assert result["backend"] == "neat-python"
    assert result["algorithm"] == "hyperneat"
    assert result["fitness"] == "xor"
    assert result["cppn"]["n_inputs"] == 4
    assert result["cppn"]["n_outputs"] == 1
    assert result["substrate"]["name"] == "layered_1d"
    assert result["substrate"]["n_inputs"] == 2
    assert result["substrate"]["n_outputs"] == 1
    assert isinstance(result["best_fitness"], float)
    assert result["n_cppn_nodes"] >= 5
