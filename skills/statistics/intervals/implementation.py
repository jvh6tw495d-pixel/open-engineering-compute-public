"""statistics.intervals entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Wraps
``oec.kernel.statistics.intervals.confidence_interval_of_mean``.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.statistics.intervals import confidence_interval_of_mean


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if "confidence_level" in inputs:
        kwargs["confidence_level"] = inputs["confidence_level"]
    if "known_variance" in inputs:
        kwargs["known_variance"] = bool(inputs["known_variance"])
    result = confidence_interval_of_mean(inputs["samples"], **kwargs)
    return {
        "result": {
            "mean": result.mean,
            "sample_standard_deviation": result.sample_standard_deviation,
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
            "converged": None,
            "backend": result.backend,
        },
    }