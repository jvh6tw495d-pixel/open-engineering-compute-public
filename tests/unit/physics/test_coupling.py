"""Unit tests for oec.physics.coupling (v2.7 weak co-sim)."""

from __future__ import annotations

import pytest

from oec.physics.coupling import (
    ConvergenceCriteria,
    CouplingConvergenceError,
    CouplingEdge,
    CouplingGraph,
    CouplingGraphError,
    InterfaceVariable,
    analytical_wire_equilibrium_temperature,
    residual_ok,
    run_coupled,
    run_solar_thermal_electrical_coupling,
    run_wire_i2r_coupling,
)
from oec.physics.coupling.checkpoint import CheckpointStore


def test_interface_variable_requires_unit() -> None:
    with pytest.raises(CouplingGraphError):
        InterfaceVariable(var_id="q", unit="")


def test_graph_manifest_roundtrip() -> None:
    edge = CouplingEdge(
        source_domain="electrical",
        target_domain="thermal",
        variables=(InterfaceVariable(var_id="q_gen", unit="W"),),
        time_owner="thermal",
        time_consumer="electrical",
    )
    g = CouplingGraph(edges=[edge], clock_owner="thermal", name="t")
    m = g.to_manifest()
    g2 = CouplingGraph.from_manifest(m)
    assert g2.clock_owner == "thermal"
    assert len(g2.edges) == 1
    assert g2.edges[0].variables[0].unit == "W"


def test_graph_rejects_self_loop() -> None:
    with pytest.raises(CouplingGraphError):
        CouplingEdge(
            source_domain="a",
            target_domain="a",
            variables=(InterfaceVariable(var_id="x", unit="1"),),
            time_owner="a",
            time_consumer="a",
        )


def test_toy_linear_converges() -> None:
    """Two toy domains: x <- 0.5 y + 1, y <- 0.5 x; fixed point x=y=2."""
    from oec.physics.coupling.graph import CouplingEdge, CouplingGraph, InterfaceVariable

    edge = CouplingEdge(
        source_domain="a",
        target_domain="b",
        variables=(InterfaceVariable(var_id="x", unit="1"),),
        time_owner="a",
        time_consumer="b",
    )
    g = CouplingGraph(edges=[edge], clock_owner="a")

    def step_a(s: dict) -> float:
        x_new = 0.5 * float(s.get("y", 0.0)) + 1.0
        old = float(s.get("x", 0.0))
        s["x"] = x_new
        return x_new - old

    def step_b(s: dict) -> float:
        y_new = 0.5 * float(s.get("x", 0.0))
        old = float(s.get("y", 0.0))
        s["y"] = y_new
        return y_new - old

    res = run_coupled(
        g,
        {"a": step_a, "b": step_b},
        initial_state={"x": 0.0, "y": 0.0},
        criteria=ConvergenceCriteria(atol=1e-10, rtol=0.0, max_iter=50, scale=1.0),
    )
    assert res.converged
    # x = 0.5 y + 1, y = 0.5 x  =>  x = 4/3, y = 2/3
    assert abs(res.state["x"] - 4.0 / 3.0) < 1e-8
    assert abs(res.state["y"] - 2.0 / 3.0) < 1e-8


def test_max_iter_raises() -> None:
    edge = CouplingEdge(
        source_domain="a",
        target_domain="b",
        variables=(InterfaceVariable(var_id="x", unit="1"),),
        time_owner="a",
        time_consumer="b",
    )
    g = CouplingGraph(edges=[edge], clock_owner="a")

    def diverge(s: dict) -> float:
        s["x"] = float(s.get("x", 0.0)) + 10.0
        return 10.0

    with pytest.raises(CouplingConvergenceError):
        run_coupled(
            g,
            {"a": diverge, "b": diverge},
            initial_state={"x": 0.0},
            criteria=ConvergenceCriteria(atol=1e-12, max_iter=3, scale=1.0),
        )


def test_checkpoint_store() -> None:
    store = CheckpointStore()
    store.push({"a": 1})
    store.push({"a": 2})
    assert store.peek() == {"a": 2}
    assert store.pop() == {"a": 2}
    assert store.pop() == {"a": 1}


def test_wire_i2r_matches_analytical() -> None:
    current = 10.0
    r0 = 0.05
    t_amb = 300.0
    ua = 5.0
    alpha = 0.0039
    t0 = 293.15
    analytical = analytical_wire_equilibrium_temperature(
        current, r0, t_amb_k=t_amb, ua_w_per_k=ua, t0_k=t0, alpha_per_k=alpha
    )
    result = run_wire_i2r_coupling(
        current,
        r0,
        t_amb_k=t_amb,
        ua_w_per_k=ua,
        t0_k=t0,
        alpha_per_k=alpha,
        criteria=ConvergenceCriteria(atol=1e-10, rtol=1e-10, max_iter=200, scale=300.0),
    )
    assert abs(result.temperature_k - analytical) <= 1e-6 + 1e-6 * abs(analytical)
    assert result.q_gen_w > 0
    assert result.iterations >= 1


def test_solar_thermal_electrical_energy_closure() -> None:
    st = run_solar_thermal_electrical_coupling(
        irradiance_w_m2=800.0,
        area_m2=2.0,
        eta0=0.18,
        t_amb_c=25.0,
        ua_w_per_k=25.0,
        gamma_per_c=-0.004,
        criteria=ConvergenceCriteria(atol=1e-9, rtol=1e-9, max_iter=100, scale=100.0),
    )
    assert abs(st.energy_closure_w) <= 1e-6 + 1e-6 * abs(st.q_solar_w)
    assert abs(st.q_solar_w - (st.p_gen_w + st.q_diss_w)) <= 1e-6
    assert st.p_gen_w > 0
    assert st.q_diss_w >= 0
    assert st.q_solar_w == pytest.approx(1600.0)


def test_residual_ok() -> None:
    c = ConvergenceCriteria(atol=1e-3, rtol=1e-3, scale=10.0)
    assert residual_ok(0.001, c)
    assert not residual_ok(1.0, c)
