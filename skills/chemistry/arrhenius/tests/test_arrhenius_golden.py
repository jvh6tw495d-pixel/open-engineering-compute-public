"""Golden for chemistry.arrhenius."""

from __future__ import annotations

import json
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_zero_ea() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "zero_ea.json").read_text(encoding="utf-8"))
    golden = GoldenCase(
        id="zero_ea.json",
        skill_id="chemistry.arrhenius",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result={
            "k": 42.0,
            "temperature_k": 300.0,
            "pre_exponential": 42.0,
            "activation_energy_j_per_mol": 0.0,
        },
        tolerance=1e-12,
        source="Ea=0 ⇒ k=A",
        justification=data["description"],
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)
