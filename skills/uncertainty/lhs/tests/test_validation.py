from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
V = validation.LhsValidator()


def test_bad_bounds() -> None:
    assert V.validate(None, {"n_samples": 2, "bounds": [[1.0, 0.0]]})  # type: ignore[arg-type]


def test_ok() -> None:
    assert not V.validate(None, {"n_samples": 2, "bounds": [[0.0, 1.0]]})  # type: ignore[arg-type]
