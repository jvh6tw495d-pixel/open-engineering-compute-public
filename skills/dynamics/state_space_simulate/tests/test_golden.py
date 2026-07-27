from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_discrete_integrator_ramp() -> None:
    out = implementation.execute(
        {
            "A": [[1.0]],
            "B": [[1.0]],
            "C": [[1.0]],
            "D": [[0.0]],
            "u": [[1.0], [1.0], [1.0]],
            "x0": [0.0],
            "dt": 1.0,
            "time_base": "discrete",
        }
    )["result"]
    assert out["x"] == [[0.0], [1.0], [2.0]]
    assert out["y"] == [[0.0], [1.0], [2.0]]
