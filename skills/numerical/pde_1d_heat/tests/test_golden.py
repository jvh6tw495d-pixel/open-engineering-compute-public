import json
from pathlib import Path

import pytest

from oec.errors import NumericalDomainError
from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_steady_zero_source_is_linear() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "steady_linear.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    x = out["result"]["x"]
    u = out["result"]["u"]
    assert out["diagnostics"]["converged"] is True
    for xi, ui in zip(x, u, strict=True):
        assert ui == pytest.approx(xi, abs=1e-10)


def test_steady_constant_source_matches_quadratic() -> None:
    # -u'' = 2 on [0,1], u(0)=u(1)=0 → u(x) = x*(1-x)
    out = implementation.execute(
        {
            "mode": "steady",
            "length": 1.0,
            "n_intervals": 40,
            "left_value": 0.0,
            "right_value": 0.0,
            "source": 2.0,
        }
    )
    x = out["result"]["x"]
    u = out["result"]["u"]
    for xi, ui in zip(x, u, strict=True):
        assert ui == pytest.approx(xi * (1.0 - xi), abs=1e-3)


def test_transient_cfl_reject() -> None:
    with pytest.raises(NumericalDomainError, match="CFL"):
        implementation.execute(
            {
                "mode": "transient",
                "length": 1.0,
                "n_intervals": 10,
                "diffusivity": 1.0,
                "dt": 1.0,
                "n_steps": 1,
            }
        )
