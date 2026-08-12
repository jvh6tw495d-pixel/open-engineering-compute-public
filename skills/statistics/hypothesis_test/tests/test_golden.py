import json
from pathlib import Path

import pytest
from scipy import stats

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_t_one_sample() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "t_one_sample.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    sample = data["input"]["sample"]
    expected = stats.ttest_1samp(sample, popmean=0.0, alternative="two-sided")
    assert out["result"]["statistic"] == pytest.approx(float(expected.statistic), rel=1e-12)
    assert out["result"]["pvalue"] == pytest.approx(float(expected.pvalue), rel=1e-12)


def test_t_two_sample_matches_scipy() -> None:
    a = [1.0, 2.0, 3.0, 4.0]
    b = [2.0, 2.5, 3.5, 4.5]
    out = implementation.execute(
        {
            "test": "t_two_sample",
            "sample_a": a,
            "sample_b": b,
            "equal_var": True,
            "alternative": "two-sided",
        }
    )
    expected = stats.ttest_ind(a, b, equal_var=True, alternative="two-sided")
    assert out["result"]["statistic"] == pytest.approx(float(expected.statistic), rel=1e-12)
    assert out["result"]["pvalue"] == pytest.approx(float(expected.pvalue), rel=1e-12)


def test_mannwhitney_runs() -> None:
    out = implementation.execute(
        {
            "test": "mannwhitney",
            "sample_a": [1.0, 2.0, 3.0],
            "sample_b": [4.0, 5.0, 6.0],
            "alternative": "two-sided",
        }
    )
    assert 0.0 <= out["result"]["pvalue"] <= 1.0
