from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_stable_continuous() -> None:
    out = implementation.execute({"A": [[-2.0]], "time_base": "continuous"})["result"]
    assert out["stable"] is True
    assert abs(out["stability_margin"] - 2.0) < 1e-12


def test_unstable_continuous() -> None:
    out = implementation.execute({"A": [[1.0]], "time_base": "continuous"})["result"]
    assert out["stable"] is False
