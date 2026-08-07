"""Golden for chemistry.batch_kinetics."""

from __future__ import annotations

import json
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_first_order_step() -> None:
    data = json.loads(
        (_SKILL_DIR / "examples" / "first_order_step.json").read_text(encoding="utf-8")
    )
    golden = GoldenCase(
        id="first_order_step.json",
        skill_id="chemistry.batch_kinetics",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result={
            "extent_step_mol": 0.1,
            "rate_mol_per_m3_s": 0.1,
            "amounts_mol": {"A": 0.9, "B": 0.1},
            "dt_s": 1.0,
        },
        tolerance=1e-12,
        source="r=k cA=0.1; dξ=r V dt=0.1",
        justification=data["description"],
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)
