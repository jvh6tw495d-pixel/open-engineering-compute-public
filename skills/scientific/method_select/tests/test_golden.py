from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")


def test_select_soo_box() -> None:
    out = implementation.execute(
        {"problem_class": "soo_box", "run_probe_benchmark": False, "seed": 0}
    )
    assert out["result"]["problem_class"] == "soo_box"
    # at least catalogs candidates even if backends missing
    assert isinstance(out["result"]["available_candidates"], list)
    assert isinstance(out["result"]["unavailable_candidates"], list)
    assert "policy" in out["result"]


def test_select_neural_tabular() -> None:
    out = implementation.execute({"problem_class": "neural_tabular"})
    assert out["result"]["message"] in ("ok", "no_available_method")
