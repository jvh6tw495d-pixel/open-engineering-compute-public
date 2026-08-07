"""Electrical ↔ thermal weak coupling (I²R losses → lumped temperature).

Gate coupling readiness (v2.7 plan):
1. time_owner = thermal
2. q_gen [W], temperature [K]
3. units explicit
4. residual |T^{k+1}-T^k|
5. checkpoint via run_coupled
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


def i2r_loss_watts(current_a: float, resistance_ohm: float) -> float:
    """Electrical Joule heating P = I²R [W]."""
    i = float(current_a)
    r = float(resistance_ohm)
    if r < 0:
        raise ValueError("resistance must be >= 0")
    return i * i * r


def resistance_at_temperature(
    r0_ohm: float,
    temperature_k: float,
    *,
    t0_k: float = 293.15,
    alpha_per_k: float = 0.0039,
) -> float:
    """Linear ρ(T): R(T) = R0 · (1 + α · (T − T0))."""
    return float(r0_ohm) * (1.0 + float(alpha_per_k) * (float(temperature_k) - float(t0_k)))


def lumped_equilibrium_temperature(
    q_gen_w: float,
    *,
    t_amb_k: float,
    ua_w_per_k: float,
) -> float:
    """Steady lumped: T = T_amb + q_gen / UA."""
    ua = float(ua_w_per_k)
    if ua <= 0:
        raise ValueError("ua_w_per_k must be > 0")
    return float(t_amb_k) + float(q_gen_w) / ua


def analytical_wire_equilibrium_temperature(
    current_a: float,
    r0_ohm: float,
    *,
    t_amb_k: float,
    ua_w_per_k: float,
    t0_k: float = 293.15,
    alpha_per_k: float = 0.0039,
) -> float:
    """Closed-form equilibrium for R(T) linear and lumped thermal.

    T = T_amb + I² R0 (1 + α (T − T0)) / UA
    => T (1 − β α) = T_amb + β (1 − α T0)  with β = I² R0 / UA
    """
    beta = (float(current_a) ** 2) * float(r0_ohm) / float(ua_w_per_k)
    denom = 1.0 - beta * float(alpha_per_k)
    if abs(denom) < 1e-15:
        raise ValueError("singular thermal-electrical equilibrium (denom ~ 0)")
    return (float(t_amb_k) + beta * (1.0 - float(alpha_per_k) * float(t0_k))) / denom


@dataclass(frozen=True)
class WireThermalState:
    """Snapshot of the coupled wire problem."""

    current_a: float
    resistance_ohm: float
    q_gen_w: float
    temperature_k: float
    iterations: int
    residual: float


def build_wire_i2r_graph() -> CouplingGraph:
    edge = CouplingEdge(
        source_domain="electrical",
        target_domain="thermal",
        variables=(
            InterfaceVariable(
                var_id="q_gen",
                unit="W",
                direction=VariableDirection.FORWARD,
                description="Joule heating I^2 R",
            ),
            InterfaceVariable(
                var_id="temperature",
                unit="K",
                direction=VariableDirection.BACKWARD,
                description="Lumped wire temperature",
            ),
        ),
        time_owner="thermal",
        time_consumer="electrical",
        edge_id="electrical__thermal_i2r",
        conversion_notes="q_gen [W] = I^2 * R(T); T [K] = T_amb + q_gen / UA",
    )
    g = CouplingGraph(edges=[edge], clock_owner="thermal", name="wire_i2r")
    g.validate()
    return g


def run_wire_i2r_coupling(
    current_a: float,
    r0_ohm: float,
    *,
    t_amb_k: float = 293.15,
    ua_w_per_k: float = 10.0,
    t0_k: float = 293.15,
    alpha_per_k: float = 0.0039,
    t_init_k: float | None = None,
    criteria: ConvergenceCriteria | None = None,
) -> WireThermalState:
    """Gauss–Seidel coupling of I²R electrical losses with lumped thermal."""
    criteria = criteria or ConvergenceCriteria(atol=1e-8, rtol=1e-8, max_iter=100, scale=300.0)
    t_init = float(t_amb_k if t_init_k is None else t_init_k)
    state: dict[str, Any] = {
        "current_a": float(current_a),
        "r0_ohm": float(r0_ohm),
        "t_amb_k": float(t_amb_k),
        "ua_w_per_k": float(ua_w_per_k),
        "t0_k": float(t0_k),
        "alpha_per_k": float(alpha_per_k),
        "temperature_k": t_init,
        "q_gen_w": 0.0,
        "resistance_ohm": float(r0_ohm),
    }

    def electrical_step(s: dict[str, Any]) -> float:
        r = resistance_at_temperature(
            s["r0_ohm"],
            s["temperature_k"],
            t0_k=s["t0_k"],
            alpha_per_k=s["alpha_per_k"],
        )
        q = i2r_loss_watts(s["current_a"], r)
        old_q = float(s.get("q_gen_w") or 0.0)
        s["resistance_ohm"] = r
        s["q_gen_w"] = q
        return q - old_q

    def thermal_step(s: dict[str, Any]) -> float:
        t_new = lumped_equilibrium_temperature(
            s["q_gen_w"],
            t_amb_k=s["t_amb_k"],
            ua_w_per_k=s["ua_w_per_k"],
        )
        t_old = float(s["temperature_k"])
        s["temperature_k"] = t_new
        return t_new - t_old

    graph = build_wire_i2r_graph()
    result: CoupledStepResult = run_coupled(
        graph,
        {"electrical": electrical_step, "thermal": thermal_step},
        initial_state=state,
        criteria=criteria,
    )
    st = result.state
    return WireThermalState(
        current_a=float(st["current_a"]),
        resistance_ohm=float(st["resistance_ohm"]),
        q_gen_w=float(st["q_gen_w"]),
        temperature_k=float(st["temperature_k"]),
        iterations=result.iterations,
        residual=result.residual,
    )


__all__ = [
    "WireThermalState",
    "analytical_wire_equilibrium_temperature",
    "build_wire_i2r_graph",
    "i2r_loss_watts",
    "lumped_equilibrium_temperature",
    "resistance_at_temperature",
    "run_wire_i2r_coupling",
]
