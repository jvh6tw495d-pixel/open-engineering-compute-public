from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
V = validation.PropagateLinearValidator()


def test_nonsquare() -> None:
    out = V.validate(None, {"jacobian": [1, 1], "covariance": [[1.0, 0.0]]})  # type: ignore[arg-type]
    assert out
