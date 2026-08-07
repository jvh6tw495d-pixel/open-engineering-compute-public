from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
V = load_skill_module(_SKILL_DIR, "validation").CvarLpValidator()


def test_bad_alpha() -> None:
    assert V.validate(
        None, {"alpha": 1.5, "loss_scenarios": [{"x": 1}]}
    )  # type: ignore[arg-type]
