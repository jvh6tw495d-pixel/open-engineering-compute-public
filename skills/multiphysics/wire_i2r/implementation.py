"""multiphysics.wire_i2r — thin adapter over coupling electrical_thermal."""

from __future__ import annotations

from typing import Any

from oec.physics.coupling import run_wire_i2r_coupling


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    for key in (
        "t_amb_k",
        "ua_w_per_k",
        "t0_k",
        "alpha_per_k",
        "t_init_k",
    ):
        if key in inputs:
            kwargs[key] = float(inputs[key])
    state = run_wire_i2r_coupling(
        float(inputs["current_a"]),
        float(inputs["r0_ohm"]),
        **kwargs,
    )
    return {
        "result": {
            "current_a": state.current_a,
            "resistance_ohm": state.resistance_ohm,
            "q_gen_w": state.q_gen_w,
            "temperature_k": state.temperature_k,
            "iterations": state.iterations,
            "residual": state.residual,
        },
        "diagnostics": {
            "converged": True,
            "iterations": state.iterations,
            "residual": state.residual,
        },
    }
