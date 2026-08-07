"""Golden cases for chemistry.fick_flux."""

from __future__ import annotations

import json
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_step_down_flux() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "step_down.json").read_text(encoding="utf-8"))
    # J = -D * (0-10)/0.1 = D * 100 = 1e-3
    golden = GoldenCase(
        id="step_down.json",
        skill_id="chemistry.fick_flux",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result={
            "flux_mol_per_m2_s": 0.001,
            "diffusivity_m2_s": 1.0e-5,
            "dc_dx_mol_per_m4": -100.0,
        },
        tolerance=1e-15,
        source="J = -D (cB-cA)/dx = 1e-5 * 100",
        justification=data["description"],
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)
