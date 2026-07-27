from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
V = validation.MorrisValidator()


def test_length_mismatch() -> None:
    out = V.validate(None, {"bounds": [[0, 1]], "coeffs": [1.0, 2.0]})  # type: ignore[arg-type]
    assert out and out[0].severity.value == "error"
