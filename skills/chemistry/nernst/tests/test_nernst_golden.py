"""Golden cases for chemistry.nernst — closed form E=E0 when Q=1."""

from __future__ import annotations

import json
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_q_equals_one_returns_e0() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "standard_state.json").read_text(encoding="utf-8"))
    golden = GoldenCase(
        id="standard_state.json",
        skill_id="chemistry.nernst",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result={
            "e_v": 1.23,
            "e0_v": 1.23,
            "n_electrons": 2,
            "temperature_k": 298.15,
            "reaction_quotient": 1.0,
        },
        tolerance=1e-12,
        source="Nernst: Q=1 ⇒ ln(Q)=0 ⇒ E=E°",
        justification=data["description"],
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)
