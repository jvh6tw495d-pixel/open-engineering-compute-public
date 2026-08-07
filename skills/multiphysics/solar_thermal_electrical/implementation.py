"""multiphysics.solar_thermal_electrical — thin coupling adapter."""

from __future__ import annotations

from typing import Any

from oec.physics.coupling import run_solar_thermal_electrical_coupling


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    for key in (
        "t_amb_c",
        "ua_w_per_k",
        "gamma_per_c",
        "t_ref_c",
        "t_init_c",
    ):
        if key in inputs:
            kwargs[key] = float(inputs[key])
    state = run_solar_thermal_electrical_coupling(
        float(inputs["irradiance_w_m2"]),
        float(inputs["area_m2"]),
        float(inputs["eta0"]),
        **kwargs,
    )
    return {
        "result": {
            "irradiance_w_m2": state.irradiance_w_m2,
            "area_m2": state.area_m2,
            "q_solar_w": state.q_solar_w,
            "temperature_c": state.temperature_c,
            "p_gen_w": state.p_gen_w,
            "q_diss_w": state.q_diss_w,
            "efficiency": state.efficiency,
            "iterations": state.iterations,
            "residual": state.residual,
            "energy_closure_w": state.energy_closure_w,
        },
        "diagnostics": {
            "converged": True,
            "iterations": state.iterations,
            "residual": state.residual,
        },
    }
