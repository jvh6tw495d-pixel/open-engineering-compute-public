"""Golden differentiation cases (v2.5 computational unification)."""

import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_quadratic_derivative_is_exact() -> None:
    data = json.loads(
        (_SKILL_DIR / "examples" / "quadratic_derivative.json").read_text(encoding="utf-8")
    )
    out = implementation.execute(data["input"])
    assert out["result"]["value"] == pytest.approx(6.0, abs=1e-6)
    assert out["diagnostics"]["method"] == "central"


def test_sine_derivative_forward() -> None:
    data = json.loads(
        (_SKILL_DIR / "examples" / "sine_derivative_forward.json").read_text(encoding="utf-8")
    )
    out = implementation.execute(data["input"])
    assert out["result"]["value"] == pytest.approx(1.0, abs=1e-4)
    assert out["diagnostics"]["method"] == "forward"


def test_explicit_step_is_honored() -> None:
    out = implementation.execute({"expression": "x**2", "at": 2.0, "step": 1e-3})
    assert out["diagnostics"]["step"] == 1e-3
    assert out["result"]["value"] == pytest.approx(4.0, abs=1e-2)
