"""statistics.bootstrap entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Wraps
``oec.kernel.statistics.bootstrap.bootstrap_ci``.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.statistics.bootstrap import bootstrap_ci


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if "statistic" in inputs:
        kwargs["statistic"] = inputs["statistic"]
    if "confidence_level" in inputs:
        kwargs["confidence_level"] = inputs["confidence_level"]
    if "n_resamples" in inputs:
        kwargs["n_resamples"] = inputs["n_resamples"]
    if "seed" in inputs:
        kwargs["seed"] = inputs["seed"]
    result = bootstrap_ci(inputs["samples"], **kwargs)
    return {
        "result": {
            "statistic": result.statistic,
            "point_estimate": result.point_estimate,
            "n": result.n,
            "n_resamples": result.n_resamples,
            "confidence_level": result.confidence_level,
            "lower": result.lower,
            "upper": result.upper,
            "backend": result.backend,
        },
        "diagnostics": {
            "n": result.n,
            "n_resamples": result.n_resamples,
            "converged": True,
            "backend": result.backend,
        },
    }