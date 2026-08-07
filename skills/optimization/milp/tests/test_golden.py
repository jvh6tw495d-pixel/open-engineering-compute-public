"""Golden MILP cases."""

import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module

pytest.importorskip("highspy")

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_knapsack_binary() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "knapsack.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    assert out["result"]["solver_status"] == "optimal"
    assert abs(out["result"]["objective_value"] - 3.0) < 1e-8
    assert abs(out["result"]["primal"]["a"] - 1.0) < 1e-8
