"""control.kalman_filter entrypoint (Joseph form + covariance checks)."""

from __future__ import annotations

from typing import Any

from oec.kernel.control.kalman import KalmanNumericalError, kalman_filter_linear


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        out = kalman_filter_linear(
            inputs["A"],
            inputs.get("B"),
            inputs["C"],
            inputs["Q"],
            inputs["R"],
            inputs["z"],
            inputs["x0"],
            inputs["P0"],
            u=inputs.get("u"),
        )
    except KalmanNumericalError as exc:
        # Surface as structured skill failure (not a bare NumPy LinAlgError).
        raise ValueError(f"{exc.code}: {exc}") from exc
    return {
        "result": out,
        "diagnostics": {
            "n_steps": out["n_steps"],
            "max_innovation_condition": out["max_innovation_condition"],
            "converged": None,
            "backend": out["backend"],
        },
    }
