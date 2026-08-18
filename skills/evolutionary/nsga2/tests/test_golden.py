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


def test_fixed_hv_reference() -> None:
    vars_ = [{"name": f"x{i}", "lower": 0.0, "upper": 1.0} for i in range(3)]
    out = implementation.execute(
        {
            "variables": vars_,
            "built_in": "bi_sphere",
            "generations": 6,
            "population": 12,
            "seed": 0,
            "hv_reference": [2.0, 2.0],
        }
    )
    assert out["result"]["hv_reference"] == [2.0, 2.0]
    assert out["result"]["runtime"]["hv_reference_mode"] == "fixed"
    assert out["result"]["hypervolume"] is not None
    assert out["result"]["hypervolume"] >= 0.0
