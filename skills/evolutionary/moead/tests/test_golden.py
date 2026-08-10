from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pymoo")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_runs_zdt1() -> None:
    vars_ = [{"name": f"x{i}", "lower": 0.0, "upper": 1.0} for i in range(5)]
    payload = {
        "variables": vars_,
        "built_in": "zdt1",
        "generations": 12,
        "population": 24,
        "seed": 0,
    }
    out = implementation.execute(payload)
    assert out["result"]["backend"] == "pymoo"
    assert out["result"]["n_nondominated"] >= 1
    assert len(out["result"]["objective_vectors"]) >= 1
