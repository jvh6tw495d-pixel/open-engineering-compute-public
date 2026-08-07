"""Solar + thermal + electrical weak coupling (PV η(T)).

Energy closure: q_solar = p_gen + q_diss (absorbed vs electrical + reject heat).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from oec.physics.coupling.co_sim import CoupledStepResult, run_coupled
from oec.physics.coupling.convergence import ConvergenceCriteria
from oec.physics.coupling.graph import (
    CouplingEdge,
    CouplingGraph,
    InterfaceVariable,
    VariableDirection,
)
from oec.physics.pv import pv_power


def efficiency_at_temperature(
    eta0: float,
    temperature_c: float,
    *,
    gamma_per_c: float = -0.004,
    t_ref_c: float = 25.0,
) -> float:
    """η(T) = η0 · (1 + γ · (T − T_ref)) with γ typically negative."""
    factor = 1.0 + float(gamma_per_c) * (float(temperature_c) - float(t_ref_c))
    return max(0.0, float(eta0) * factor)


@dataclass(frozen=True)
class SolarThermalElectricalState:
    irradiance_w_m2: float
    area_m2: float
    q_solar_w: float
    temperature_c: float
    p_gen_w: float
    q_diss_w: float
    efficiency: float
    iterations: int
    residual: float
    energy_closure_w: float


def build_solar_thermal_electrical_graph() -> CouplingGraph:
    e1 = CouplingEdge(
        source_domain="solar",
        target_domain="thermal",
        variables=(
            InterfaceVariable(
                var_id="q_solar",
                unit="W",
                direction=VariableDirection.FORWARD,
                description="Captured solar power on array plane",
            ),
        ),
        time_owner="solar",
        time_consumer="thermal",
        edge_id="solar__thermal",
    )
    e2 = CouplingEdge(
        source_domain="thermal",
        target_domain="electrical",
        variables=(
            InterfaceVariable(
                var_id="temperature",
                unit="degC",
                direction=VariableDirection.FORWARD,
                description="Cell temperature",
            ),
        ),
        time_owner="thermal",
        time_consumer="electrical",
        edge_id="thermal__electrical",
    )
    e3 = CouplingEdge(
        source_domain="electrical",
        target_domain="thermal",
        variables=(
            InterfaceVariable(
                var_id="p_gen",
                unit="W",
                direction=VariableDirection.FORWARD,
                description="Electrical generation",
            ),
            InterfaceVariable(
                var_id="q_diss",
                unit="W",
                direction=VariableDirection.FORWARD,
                description="Heat rejected = q_solar - p_gen",
            ),
        ),
        time_owner="electrical",
        time_consumer="thermal",
        edge_id="electrical__thermal_balance",
    )
    g = CouplingGraph(
        edges=[e1, e2, e3],
        clock_owner="solar",
        name="solar_thermal_electrical",
    )
    g.validate()
    return g


def run_solar_thermal_electrical_coupling(
    irradiance_w_m2: float,
    area_m2: float,
    eta0: float,
    *,
    t_amb_c: float = 25.0,
    ua_w_per_k: float = 20.0,
    gamma_per_c: float = -0.004,
    t_ref_c: float = 25.0,
    t_init_c: float | None = None,
    criteria: ConvergenceCriteria | None = None,
) -> SolarThermalElectricalState:
    """Couple PV capture, cell temperature, and electrical generation."""
    criteria = criteria or ConvergenceCriteria(atol=1e-8, rtol=1e-8, max_iter=100, scale=100.0)
    g = float(irradiance_w_m2)
    a = float(area_m2)
    # Optical capture (before electrical conversion) as energy rate on plane * area
    # Use eta=1 path for "absorbed" bookkeeping separately from electrical η.
    q_solar = g * a  # W of irradiance on array (planning model; not optical loss detail)
    t0 = float(t_amb_c if t_init_c is None else t_init_c)
    state: dict[str, Any] = {
        "irradiance_w_m2": g,
        "area_m2": a,
        "eta0": float(eta0),
        "gamma_per_c": float(gamma_per_c),
        "t_ref_c": float(t_ref_c),
        "t_amb_c": float(t_amb_c),
        "ua_w_per_k": float(ua_w_per_k),
        "q_solar_w": q_solar,
        "temperature_c": t0,
        "p_gen_w": 0.0,
        "q_diss_w": 0.0,
        "efficiency": float(eta0),
    }

    def solar_step(s: dict[str, Any]) -> float:
        # fixed source for step
        qs = float(s["irradiance_w_m2"]) * float(s["area_m2"])
        old = float(s.get("q_solar_w") or 0.0)
        s["q_solar_w"] = qs
        return qs - old

    def thermal_step(s: dict[str, Any]) -> float:
        # Cell heating: absorbed non-converted power rejected as heat + ambient
        # T = T_amb + q_diss / UA
        q_diss = float(s.get("q_diss_w") or 0.0)
        t_new = float(s["t_amb_c"]) + q_diss / float(s["ua_w_per_k"])
        t_old = float(s["temperature_c"])
        s["temperature_c"] = t_new
        return t_new - t_old

    def electrical_step(s: dict[str, Any]) -> float:
        eta = efficiency_at_temperature(
            s["eta0"],
            s["temperature_c"],
            gamma_per_c=s["gamma_per_c"],
            t_ref_c=s["t_ref_c"],
        )
        # Use physics.pv owner for power at current η
        p = float(
            pv_power(
                irradiance=s["irradiance_w_m2"],
                area=s["area_m2"],
                efficiency=eta,
            )["power"]
        )
        qs = float(s["q_solar_w"])
        q_diss = max(0.0, qs - p)
        s["efficiency"] = eta
        s["p_gen_w"] = p
        s["q_diss_w"] = q_diss
        # residual: energy closure
        return qs - (p + q_diss)

    graph = build_solar_thermal_electrical_graph()
    # Order: solar → thermal → electrical per plan W4
    from oec.physics.coupling.schedule import CouplingSchedule

    schedule = CouplingSchedule(
        clock_owner="solar",
        domain_order=("solar", "thermal", "electrical"),
        dt=1.0,
        unit="s",
    )
    result: CoupledStepResult = run_coupled(
        graph,
        {
            "solar": solar_step,
            "thermal": thermal_step,
            "electrical": electrical_step,
        },
        initial_state=state,
        schedule=schedule,
        criteria=criteria,
    )
    st = result.state
    closure = float(st["q_solar_w"]) - (float(st["p_gen_w"]) + float(st["q_diss_w"]))
    return SolarThermalElectricalState(
        irradiance_w_m2=float(st["irradiance_w_m2"]),
        area_m2=float(st["area_m2"]),
        q_solar_w=float(st["q_solar_w"]),
        temperature_c=float(st["temperature_c"]),
        p_gen_w=float(st["p_gen_w"]),
        q_diss_w=float(st["q_diss_w"]),
        efficiency=float(st["efficiency"]),
        iterations=result.iterations,
        residual=result.residual,
        energy_closure_w=closure,
    )


__all__ = [
    "SolarThermalElectricalState",
    "build_solar_thermal_electrical_graph",
    "efficiency_at_temperature",
    "run_solar_thermal_electrical_coupling",
]
