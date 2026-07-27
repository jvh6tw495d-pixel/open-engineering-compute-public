from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
V = validation.StateSpaceValidator()


def test_nonsquare() -> None:
    assert V.validate(None, {"A": [[1.0, 0.0]], "dt": 1.0})  # type: ignore[arg-type]
