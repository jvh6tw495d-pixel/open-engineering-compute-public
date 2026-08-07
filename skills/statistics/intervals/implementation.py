"""statistics.intervals entrypoint (skill 0.2.0)."""

from __future__ import annotations

from typing import Any

from oec.kernel.statistics.intervals import confidence_interval_of_mean


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if "confidence_level" in inputs:
        kwargs["confidence_level"] = inputs["confidence_level"]
    if inputs.get("population_standard_deviation") is not None:
        kwargs["population_standard_deviation"] = float(
            inputs["population_standard_deviation"]
        )
    # Explicit rejection of removed API
    if "known_variance" in inputs:
        raise ValueError(
            "known_variance was removed in 0.2.0; use population_standard_deviation"
        )
    result = confidence_interval_of_mean(inputs["samples"], **kwargs)
    return {
        "result": {
            "mean": result.mean,
            "sample_standard_deviation": result.sample_standard_deviation,
            "population_standard_deviation": result.population_standard_deviation,
            "dispersion_used": result.dispersion_used,
            "n": result.n,
            "confidence_level": result.confidence_level,
            "distribution": result.distribution,
            "df": result.df,
            "lower": result.lower,
            "upper": result.upper,
            "half_width": result.half_width,
            "backend": result.backend,
        },
        "diagnostics": {
            "n": result.n,
            "distribution": result.distribution,
            "dispersion_used": result.dispersion_used,
            "converged": None,
            "backend": result.backend,
        },
    }
