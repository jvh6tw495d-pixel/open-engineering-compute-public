"""Golden for electrical.harmonics_thd."""

from __future__ import annotations

import json
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_simple_thd() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "simple_thd.json").read_text(encoding="utf-8"))
    golden = GoldenCase(
        id="simple_thd.json",
        skill_id="electrical.harmonics_thd",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result={"thd": 0.05, "thd_percent": 5.0},
        tolerance=1e-12,
        source="sqrt(3^2+4^2)/100 = 5/100",
        justification=data["description"],
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)
