"""W1 kernel tests: closed-catalog hypothesis tests."""

from __future__ import annotations

import pytest
from scipy import stats

from oec.errors import NumericalDomainError
from oec.kernel.statistics.hypothesis import run_hypothesis_test


def test_t_one_sample_matches_scipy() -> None:
    sample = [1.0, 2.0, 3.0, 4.0, 5.0]
    out = run_hypothesis_test(test="t_one_sample", sample=sample, popmean=3.0)
    expected = stats.ttest_1samp(sample, popmean=3.0)
    assert out["statistic"] == pytest.approx(float(expected.statistic), rel=1e-12)
    assert out["pvalue"] == pytest.approx(float(expected.pvalue), rel=1e-12)


def test_unknown_test() -> None:
    with pytest.raises(NumericalDomainError):
        run_hypothesis_test(test="anova", sample=[1.0, 2.0])
