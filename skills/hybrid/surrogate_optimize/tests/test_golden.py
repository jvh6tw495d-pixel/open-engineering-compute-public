from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")
pytest.importorskip("nevergrad")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = [pytest.mark.neural, pytest.mark.evolutionary]


def test_surrogate_pipeline() -> None:
    out = implementation.execute(
        {
            "built_in": "sphere",
            "n_var": 2,
            "n_train": 40,
            "surrogate_epochs": 20,
            "evo_budget": 40,
            "seed": 0,
            "device": "cpu",
            "n_verify": 3,
        }
    )
    assert out["result"]["pipeline"].startswith("sample")
    assert out["result"]["high_fidelity"]["accepted_as_engineering_truth"] is False
    assert "best_true" in out["result"]["high_fidelity"]
