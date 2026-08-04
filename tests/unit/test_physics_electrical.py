"""P1 canonical meshed DC linear power flow (D4) — Wave 3 slice 3.2."""

from __future__ import annotations

import pytest

from oec.physics.electrical import (
    DC_POWER_FLOW_ASSUMPTIONS,
    ElectricalNetworkError,
    NetworkLine,
    dc_power_flow,
)


def test_two_bus_radial_subset_matches_hand_solved_dc_power_flow() -> None:
    # Single line A(slack)-B, B_AB = 5 pu. Injection: A = -1 pu (load), B = +1 pu (generation).
    # KCL at B: injection_B = B_AB * (theta_B - theta_A) => theta_B = 1.0 / 5 = 0.2 rad.
    # Flow A->B = B_AB * (theta_A - theta_B) = 5 * (0 - 0.2) = -1 pu (power actually flows B->A).
    lines = [NetworkLine(from_bus="A", to_bus="B", susceptance=5.0)]
    result = dc_power_flow(lines, {"A": -1.0, "B": 1.0}, slack_bus="A")

    assert result.angles["A"] == pytest.approx(0.0)
    assert result.angles["B"] == pytest.approx(0.2)
    assert len(result.flows) == 1
    assert result.flows[0].power == pytest.approx(-1.0)
    assert result.balance.balanced is True
    assert all(check.balanced for check in result.node_balance.values())


def test_meshed_triangle_network_is_not_radial_and_balances() -> None:
    lines = [
        NetworkLine(from_bus="A", to_bus="B", susceptance=10.0),
        NetworkLine(from_bus="B", to_bus="C", susceptance=10.0),
        NetworkLine(from_bus="A", to_bus="C", susceptance=10.0),
    ]
    injections = {"A": -1.0, "B": 0.4, "C": 0.6}

    result = dc_power_flow(lines, injections, slack_bus="A")

    assert result.balance.balanced is True
    assert result.balance.residual == pytest.approx(0.0, abs=1e-9)
    # meshed: 3 lines among 3 buses, more edges than a spanning tree (radial) would have
    assert len(result.flows) == 3
    # KCL holds at every non-slack bus explicitly (not just in aggregate)
    for flow_check in result.node_balance.values():
        assert flow_check.balanced


def test_inconsistent_slack_injection_produces_unbalanced_kcl() -> None:
    lines = [NetworkLine(from_bus="A", to_bus="B", susceptance=5.0)]
    # Sum of injections != 0 for a lossless network -> slack residual and aggregate nonzero.
    result = dc_power_flow(lines, {"A": 0.0, "B": 1.0}, slack_bus="A", atol=1e-9, rtol=1e-9)

    assert result.node_balance["A"].balanced is False
    assert result.balance.balanced is False
    assert result.balance.residual == pytest.approx(1.0)


def test_disconnected_network_is_rejected() -> None:
    lines = [
        NetworkLine(from_bus="A", to_bus="B", susceptance=5.0),
        NetworkLine(from_bus="C", to_bus="D", susceptance=5.0),
    ]
    with pytest.raises(ElectricalNetworkError, match="not connected"):
        dc_power_flow(lines, {"A": -1.0, "B": 1.0, "C": -1.0, "D": 1.0}, slack_bus="A")


def test_missing_injection_is_rejected() -> None:
    lines = [NetworkLine(from_bus="A", to_bus="B", susceptance=5.0)]
    with pytest.raises(ElectricalNetworkError, match="injections must be supplied"):
        dc_power_flow(lines, {"A": -1.0}, slack_bus="A")


def test_unknown_slack_bus_is_rejected() -> None:
    lines = [NetworkLine(from_bus="A", to_bus="B", susceptance=5.0)]
    with pytest.raises(ElectricalNetworkError, match="slack bus"):
        dc_power_flow(lines, {"A": -1.0, "B": 1.0}, slack_bus="Z")


def test_self_loop_line_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot connect a bus to itself"):
        NetworkLine(from_bus="A", to_bus="A", susceptance=1.0)


def test_assumptions_are_documented_and_attached_to_the_result() -> None:
    lines = [NetworkLine(from_bus="A", to_bus="B", susceptance=5.0)]
    result = dc_power_flow(lines, {"A": -1.0, "B": 1.0}, slack_bus="A")

    assert result.assumptions == DC_POWER_FLOW_ASSUMPTIONS
    assert any("connected" in assumption.text for assumption in result.assumptions)
