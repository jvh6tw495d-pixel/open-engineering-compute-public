"""Golden for multiphysics.wire_i2r (alpha=0 closed form)."""

from __future__ import annotations

import json
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_alpha_zero_temperature() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "alpha_zero.json").read_text(encoding="utf-8"))
    # I=10, R=0.1 → q=10 W; UA=1 → dT=10 K; T=303.15
    out = implementation.execute(data["input"])["result"]
    assert abs(out["temperature_k"] - 303.15) < 1e-6
    assert abs(out["q_gen_w"] - 10.0) < 1e-6
    assert abs(out["resistance_ohm"] - 0.1) < 1e-9
    assert abs(out["current_a"] - 10.0) < 1e-12
    assert out["iterations"] >= 1
    assert out["residual"] >= 0.0
