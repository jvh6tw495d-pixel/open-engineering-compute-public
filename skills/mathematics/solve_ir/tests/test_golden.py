"""Golden Math IR cases (v2.2)."""

import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_lp_example_optimal() -> None:
    pytest.importorskip("highspy")
    data = json.loads((_SKILL_DIR / "examples" / "lp_example.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    assert out["result"]["problem_class"] == "linear_program"
    assert out["result"]["backend"] == "highs"
    assert abs(out["result"]["solution"]["objective_value"] - 1.0) < 1e-8
    assert out["diagnostics"]["converged"] is True


def test_scalar_root_example_converges() -> None:
    data = json.loads(
        (_SKILL_DIR / "examples" / "scalar_root_example.json").read_text(encoding="utf-8")
    )
    out = implementation.execute(data["input"])
    assert out["result"]["problem_class"] == "scalar_root"
    assert out["result"]["backend"] == "scipy"
    assert abs(out["result"]["solution"]["root"] - 2.0) < 1e-6
    assert out["diagnostics"]["converged"] is True
