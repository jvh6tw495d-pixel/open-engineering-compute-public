from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_proportional_only() -> None:
    out = implementation.execute(
        {
            "reference": [1.0, 1.0, 1.0],
            "measurement": [0.0, 0.0, 0.0],
            "kp": 2.0,
            "ki": 0.0,
            "kd": 0.0,
            "dt": 0.1,
        }
    )["result"]
    assert out["u"] == [2.0, 2.0, 2.0]
    assert out["error"] == [1.0, 1.0, 1.0]
