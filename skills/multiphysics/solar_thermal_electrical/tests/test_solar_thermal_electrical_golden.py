"""Golden for multiphysics.solar_thermal_electrical — energy closure."""

from __future__ import annotations

import json
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_energy_closure() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "stc_like.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])["result"]
    assert abs(out["q_solar_w"] - 1000.0) < 1e-6
    # Closure: q_solar ≈ p_gen + q_diss
    assert (
        abs(out["energy_closure_w"]) < 1e-4
        or abs(out["q_solar_w"] - (out["p_gen_w"] + out["q_diss_w"])) < 1e-4
    )
    assert out["p_gen_w"] > 0.0
    assert out["efficiency"] > 0.0
