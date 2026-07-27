from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_independent_sum_variance() -> None:
    out = implementation.execute(
        {
            "jacobian": [1.0, 1.0],
            "covariance": [[1.0, 0.0], [0.0, 1.0]],
        }
    )["result"]
    assert abs(out["variance"] - 2.0) < 1e-12
    assert abs(out["std"] - 2.0**0.5) < 1e-12
