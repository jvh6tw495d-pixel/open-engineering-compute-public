import json
from math import exp, pi, sqrt
from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_norm_pdf_at_zero() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "norm_pdf.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    expected = 1.0 / sqrt(2.0 * pi)
    assert out["result"]["value"] == pytest.approx(expected, rel=1e-9)


def test_norm_cdf_median() -> None:
    out = implementation.execute(
        {
            "distribution": "norm",
            "operation": "cdf",
            "params": {"loc": 0.0, "scale": 1.0},
            "x": 0.0,
        }
    )
    assert out["result"]["value"] == pytest.approx(0.5, rel=1e-12)


def test_norm_ppf_median() -> None:
    out = implementation.execute(
        {
            "distribution": "norm",
            "operation": "ppf",
            "params": {"loc": 0.0, "scale": 1.0},
            "p": 0.5,
        }
    )
    assert out["result"]["value"] == pytest.approx(0.0, abs=1e-12)


def test_sample_reproducible() -> None:
    inp = {
        "distribution": "norm",
        "operation": "sample",
        "params": {"loc": 0.0, "scale": 1.0},
        "n_samples": 5,
        "seed": 0,
    }
    a = implementation.execute(inp)["result"]["samples"]
    b = implementation.execute(inp)["result"]["samples"]
    assert a == b
    assert len(a) == 5


def test_norm_pdf_matches_formula() -> None:
    x = 1.0
    out = implementation.execute(
        {
            "distribution": "norm",
            "operation": "pdf",
            "params": {"loc": 0.0, "scale": 1.0},
            "x": x,
        }
    )
    expected = exp(-0.5 * x * x) / sqrt(2.0 * pi)
    assert out["result"]["value"] == pytest.approx(expected, rel=1e-9)
