from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
V = validation.StabilityValidator()


def test_square_required() -> None:
    assert V.validate(None, {"A": [[1.0, 2.0]]})  # type: ignore[arg-type]
