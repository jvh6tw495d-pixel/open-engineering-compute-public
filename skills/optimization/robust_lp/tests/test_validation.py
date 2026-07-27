from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
V = load_skill_module(_SKILL_DIR, "validation").RobustLpValidator()


def test_empty_unc() -> None:
    assert V.validate(None, {"rhs_uncertainty": {}})  # type: ignore[arg-type]
