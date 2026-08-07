"""Golden for chemistry.equilibrium."""

from __future__ import annotations

import json
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_equal_at_eq() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "equal_kc1.json").read_text(encoding="utf-8"))
    golden = GoldenCase(
        id="equal_kc1.json",
        skill_id="chemistry.equilibrium",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result={
            "qc": 1.0,
            "kc": 1.0,
            "driving_force": 0.0,
            "at_equilibrium": True,
        },
        tolerance=1e-12,
        source="A⇌B, nA=nB, V=1, Kc=1 ⇒ Qc=1",
        justification=data["description"],
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)
