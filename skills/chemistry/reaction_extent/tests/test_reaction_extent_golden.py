"""Golden cases for chemistry.reaction_extent."""

from __future__ import annotations

import json
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_o2_limited_extent() -> None:
    data = json.loads(
        (_SKILL_DIR / "examples" / "complete_o2_limit.json").read_text(encoding="utf-8")
    )
    golden = GoldenCase(
        id="complete_o2_limit.json",
        skill_id="chemistry.reaction_extent",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result={
            "extent_mol": 1.0,
            "max_extent_mol": 1.0,
            "amounts_mol": {"H2": 2.0, "O2": 0.0, "H2O": 2.0},
            "atom_balance_ok": True,
        },
        tolerance=1e-12,
        source="2 H2 + O2 → 2 H2O; ξ=1 on (4,1,0) → (2,0,2)",
        justification=data["description"],
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)
