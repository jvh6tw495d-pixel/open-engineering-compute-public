"""dynamics.state_space_simulate entrypoint."""

from __future__ import annotations

from typing import Any

from oec.kernel.dynamics.state_space import simulate_state_space


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = simulate_state_space(
        inputs["A"],
        inputs["B"],
        inputs["C"],
        inputs["D"],
        inputs["u"],
        inputs["x0"],
        dt=float(inputs["dt"]),
        time_base=str(inputs.get("time_base", "discrete")),
    )
    return {
        "result": out,
        "diagnostics": {
            "n_steps": out["n_steps"],
            "converged": None,
            "backend": out["backend"],
        },
    }
