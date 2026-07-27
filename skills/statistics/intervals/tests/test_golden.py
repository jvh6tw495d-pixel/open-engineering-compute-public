"""Golden cases for statistics.intervals (v2.3 Wave A)."""

from __future__ import annotations

import math
from pathlib import Path

from scipy import stats

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_mean_and_shape_of_one_to_five() -> None:
    golden = GoldenCase(
        id="ci_of_one_to_five.json",
        skill_id="statistics.intervals",
        skill_version="0.1.0",
        inputs={"samples": [1.0, 2.0, 3.0, 4.0, 5.0], "confidence_level": 0.95},
        expected_result={
            "mean": 3.0,
            "n": 5,
            "confidence_level": 0.95,
            "distribution": "student_t",
            "backend": "scipy.stats",
        },
        tolerance=1e-12,
        source="closed form: mean=3, n=5 sample of [1..5]",
        justification=(
            "Independent verification of summary fields; "
            "detailed half-width is tested separately below."
        ),
    )
    out = implementation.execute(golden.inputs)
    actual = {
        "mean": out["result"]["mean"],
        "n": out["result"]["n"],
        "confidence_level": out["result"]["confidence_level"],
        "distribution": out["result"]["distribution"],
        "backend": out["result"]["backend"],
    }
    assert_matches_golden(actual, golden)


def test_half_width_matches_closed_form_t_interval() -> None:
    samples = [1.0, 2.0, 3.0, 4.0, 5.0]
    n = len(samples)
    mean = sum(samples) / n
    s = math.sqrt(sum((x - mean) ** 2 for x in samples) / (n - 1))
    df = n - 1
    expected_half = stats.t.ppf(0.975, df) * s / math.sqrt(n)
    out = implementation.execute({"samples": samples, "confidence_level": 0.95})
    assert math.isclose(out["result"]["half_width"], float(expected_half), rel_tol=1e-9)


def test_interval_contains_mean() -> None:
    out = implementation.execute(
        {"samples": [1.0, 2.0, 3.0, 4.0, 5.0], "confidence_level": 0.95}
    )
    assert out["result"]["lower"] < out["result"]["mean"] < out["result"]["upper"]