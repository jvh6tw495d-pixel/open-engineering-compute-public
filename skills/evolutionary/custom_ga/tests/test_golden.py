from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("deap")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_custom_ga_runs() -> None:
    out = implementation.execute({"built_in": "sphere", "n_var": 2, "generations": 15, "seed": 1})
    assert out["result"]["backend"] == "deap"
