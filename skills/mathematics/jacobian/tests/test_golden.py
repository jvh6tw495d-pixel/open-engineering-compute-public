import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_quadratic_jacobian() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "quadratic.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    # f1 = x^2 + y → [2x, 1] = [2, 1] at (1,2)
    # f2 = x*y → [y, x] = [2, 1]
    j = out["result"]["jacobian"]
    assert j[0][0] == pytest.approx(2.0, abs=1e-5)
    assert j[0][1] == pytest.approx(1.0, abs=1e-5)
    assert j[1][0] == pytest.approx(2.0, abs=1e-5)
    assert j[1][1] == pytest.approx(1.0, abs=1e-5)
    assert out["result"]["shape"] == [2, 2]


def test_gradient_of_scalar() -> None:
    out = implementation.execute(
        {
            "expressions": ["x**2 + y**2"],
            "variables": ["x", "y"],
            "at": [3.0, 4.0],
            "method": "central",
        }
    )
    j = out["result"]["jacobian"]
    assert j[0][0] == pytest.approx(6.0, abs=1e-5)
    assert j[0][1] == pytest.approx(8.0, abs=1e-5)
