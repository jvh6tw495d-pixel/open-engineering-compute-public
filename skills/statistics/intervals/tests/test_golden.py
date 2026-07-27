"""Golden + adversarial cases for statistics.intervals 0.2.0 (A23-01)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from scipy import stats

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_mean_and_shape_of_one_to_five() -> None:
    out = implementation.execute(
        {"samples": [1.0, 2.0, 3.0, 4.0, 5.0], "confidence_level": 0.95}
    )["result"]
    assert out["mean"] == 3.0
    assert out["n"] == 5
    assert out["distribution"] == "student_t"
    assert out["dispersion_used"] == "sample_standard_deviation"
    assert out["population_standard_deviation"] is None


def test_half_width_matches_scipy_t_interval() -> None:
    samples = [1.0, 2.0, 3.0, 4.0, 5.0]
    n = len(samples)
    mean = sum(samples) / n
    s = math.sqrt(sum((x - mean) ** 2 for x in samples) / (n - 1))
    expected_half = stats.t.ppf(0.975, n - 1) * s / math.sqrt(n)
    lo, hi = stats.t.interval(0.95, n - 1, loc=mean, scale=s / math.sqrt(n))
    out = implementation.execute({"samples": samples, "confidence_level": 0.95})["result"]
    assert math.isclose(out["half_width"], float(expected_half), rel_tol=1e-9)
    assert math.isclose(out["lower"], float(lo), rel_tol=1e-9)
    assert math.isclose(out["upper"], float(hi), rel_tol=1e-9)


def test_z_interval_single_observation_with_population_sigma() -> None:
    # n=1, mean=10, sigma=2, 95% -> half = 1.95996... * 2 / 1
    z = float(stats.norm.ppf(0.975))
    expected_half = z * 2.0
    out = implementation.execute(
        {
            "samples": [10.0],
            "confidence_level": 0.95,
            "population_standard_deviation": 2.0,
        }
    )["result"]
    assert out["distribution"] == "gaussian"
    assert out["dispersion_used"] == "population_standard_deviation"
    assert out["population_standard_deviation"] == 2.0
    assert math.isclose(out["half_width"], expected_half, rel_tol=1e-9)
    assert math.isclose(out["lower"], 10.0 - expected_half, rel_tol=1e-9)
    assert math.isclose(out["upper"], 10.0 + expected_half, rel_tol=1e-9)


def test_z_interval_matches_closed_form() -> None:
    samples = [1.0, 3.0, 5.0]
    sigma = 1.5
    n = 3
    mean = 3.0
    z = float(stats.norm.ppf(0.975))
    expected_half = z * sigma / math.sqrt(n)
    out = implementation.execute(
        {
            "samples": samples,
            "confidence_level": 0.95,
            "population_standard_deviation": sigma,
        }
    )["result"]
    assert out["mean"] == mean
    assert math.isclose(out["half_width"], expected_half, rel_tol=1e-12)


def test_rejects_known_variance_field() -> None:
    with pytest.raises(ValueError, match="known_variance"):
        implementation.execute(
            {"samples": [1.0, 2.0], "known_variance": True}
        )


def test_rejects_nonpositive_sigma() -> None:
    with pytest.raises(ValueError, match="population_standard_deviation"):
        implementation.execute(
            {
                "samples": [1.0],
                "population_standard_deviation": 0.0,
            }
        )


def test_rejects_nan_sigma() -> None:
    with pytest.raises(ValueError, match="population_standard_deviation"):
        implementation.execute(
            {
                "samples": [1.0],
                "population_standard_deviation": float("nan"),
            }
        )


def test_student_t_requires_n_ge_2() -> None:
    with pytest.raises(ValueError, match="n >= 2"):
        implementation.execute({"samples": [1.0]})
