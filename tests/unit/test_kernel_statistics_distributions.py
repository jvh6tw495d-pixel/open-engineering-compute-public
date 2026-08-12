"""W1 kernel tests: closed-catalog distributions."""

from __future__ import annotations

from math import pi, sqrt

import pytest

from oec.errors import NumericalDomainError
from oec.kernel.statistics.distributions import evaluate_distribution


def test_norm_pdf_at_zero() -> None:
    out = evaluate_distribution(
        distribution="norm", operation="pdf", params={"loc": 0.0, "scale": 1.0}, x=0.0
    )
    assert out["value"] == pytest.approx(1.0 / sqrt(2.0 * pi), rel=1e-12)


def test_unknown_distribution() -> None:
    with pytest.raises(NumericalDomainError):
        evaluate_distribution(distribution="weird", operation="pdf", x=0.0)


def test_ppf_requires_p() -> None:
    with pytest.raises(NumericalDomainError):
        evaluate_distribution(distribution="norm", operation="ppf")
