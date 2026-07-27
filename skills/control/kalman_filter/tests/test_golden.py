from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_static_scalar_moves_toward_measurement() -> None:
    out = implementation.execute(
        {
            "A": [[1.0]],
            "C": [[1.0]],
            "Q": [[0.0]],
            "R": [[1.0]],
            "z": [[5.0]],
            "x0": [0.0],
            "P0": [[1.0]],
        }
    )["result"]
    assert abs(out["x_filtered"][0][0] - 2.5) < 1e-12
    assert out["method"] == "discrete_linear_kalman_joseph"
    assert "p_filtered" in out
    assert "kalman_gains" in out
