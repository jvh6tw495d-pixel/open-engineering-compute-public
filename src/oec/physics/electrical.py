"""P1 — canonical meshed DC linear power flow (D4).

This module is the *only* canonical P1 power-flow model in the Physics
Foundation v0: a linear, lossless, meshed active-power flow over a
susceptance (``B``) network, solved relative to a slack bus. AC power flow,
machine models, and LP/OPF dispatch are explicitly out of scope (D4) — a
radial branch-flow simplification is **not** a substitute for this canonical
model.

This is a documented façade over the classical electrical engineering the
project already exposes as ``skills/electrical/*`` (``three_phase_power``,
``voltage_drop``, ``power_factor_correction``, ...). Those skills are
per-quantity point calculators and are untouched by this wave; this module
instead solves a network-level linear system and reports it through the
:mod:`oec.physics` domain objects and conservation owner.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from oec.core.types import Assumption
from oec.physics.conservation import aggregate_balance
from oec.physics.errors import PhysicsError
from oec.physics.laws import ConservationLaw
from oec.physics.result import ConservationCheck
from oec.physics.types import PhysicsDomain, ValidityFrame

DC_POWER_FLOW_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(
        text="Linear network; resistive (I^2 R) losses are neglected (classic DC power-flow model)",
        source="D4",
    ),
    Assumption(text="Flat voltage magnitude: |V| ~= 1 pu at every bus", source="D4"),
    Assumption(
        text="Only active power is modeled; reactive power, machines, and sequence components"
        " are out of scope",
        source="D4",
    ),
    Assumption(text="Steady-state operating point", source="D4"),
    Assumption(text="The network graph is connected", source="D4"),
    Assumption(
        text="Susceptances and injections are expressed in a dimensionless per-unit (pu) system",
        source="P1 v0",
    ),
)

_VALIDITY = ValidityFrame(
    domains=(PhysicsDomain.ELECTRICAL,),
    description="Meshed DC linear active-power flow, per D4",
    constraints=("connected graph", "flat |V| ~= 1 pu", "active power only"),
)

_KCL_LAW = ConservationLaw(
    id="electrical.dc_power_flow.kcl",
    name="Nodal KCL residual (active power, DC linear model)",
    hypotheses=DC_POWER_FLOW_ASSUMPTIONS,
    validity=_VALIDITY,
    references=("D4 — v2.6-EXECUTION-PLAN.md",),
    evaluator=lambda state: float(state["injection"] - state["outflow"]),
)


class ElectricalNetworkError(PhysicsError):
    """Raised when a DC power-flow network topology or request is invalid."""

    default_code = "electrical_network_error"


class NetworkLine(BaseModel):
    """One meshed-network branch between two buses and its susceptance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    from_bus: str = Field(min_length=1)
    to_bus: str = Field(min_length=1)
    susceptance: float = Field(gt=0.0, description="B_ij = 1 / X_ij, per-unit (pu)")

    @field_validator("to_bus")
    @classmethod
    def _distinct_endpoints(cls, value: str, info: ValidationInfo) -> str:
        from_bus = info.data.get("from_bus")
        if from_bus is not None and value == from_bus:
            raise ValueError("a line cannot connect a bus to itself")
        return value


class LineFlow(BaseModel):
    """Active-power flow computed on one line, oriented from_bus -> to_bus."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    from_bus: str
    to_bus: str
    power: float = Field(description="P_ij = B_ij * (theta_i - theta_j), pu; positive from->to")


class DcPowerFlowResult(BaseModel):
    """Auditable outcome of the meshed DC linear power-flow solve."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    slack_bus: str
    angles: dict[str, float] = Field(description="theta_i in rad, relative to the slack bus")
    flows: tuple[LineFlow, ...]
    node_balance: dict[str, ConservationCheck]
    balance: ConservationCheck
    assumptions: tuple[Assumption, ...]


def _connected_buses(buses: Sequence[str], lines: Sequence[NetworkLine]) -> set[str]:
    adjacency: dict[str, set[str]] = {bus: set() for bus in buses}
    for line in lines:
        adjacency[line.from_bus].add(line.to_bus)
        adjacency[line.to_bus].add(line.from_bus)

    start = buses[0]
    seen = {start}
    frontier = [start]
    while frontier:
        current = frontier.pop()
        for neighbor in adjacency[current] - seen:
            seen.add(neighbor)
            frontier.append(neighbor)
    return seen


def dc_power_flow(
    lines: Sequence[NetworkLine],
    injections: Mapping[str, float],
    *,
    slack_bus: str,
    atol: float = 1e-9,
    rtol: float = 1e-9,
) -> DcPowerFlowResult:
    """Solve the canonical meshed DC linear power flow (D4) and check KCL.

    ``injections`` must supply one active-power injection (pu, positive =
    generation / power entering the bus) for every bus that appears in
    ``lines``, including the slack bus: the slack entry is not solved for,
    it is checked — a network built from a lossless ``B`` matrix must have
    ``sum(injections) == 0``, and any mismatch shows up as a nonzero KCL
    residual at the slack bus (and in the network-level aggregate).

    Every KCL residual is produced by the executed :data:`_KCL_LAW`
    :class:`~oec.physics.laws.ConservationLaw`; the per-node checks are
    aggregated into ``balance`` via :func:`oec.physics.conservation.aggregate_balance`
    (the D5 owner), never by a locally reimplemented tolerance formula.
    """
    if len(lines) == 0:
        raise ElectricalNetworkError("dc_power_flow requires at least one line")

    buses = sorted({line.from_bus for line in lines} | {line.to_bus for line in lines})
    if slack_bus not in buses:
        raise ElectricalNetworkError(
            f"slack bus {slack_bus!r} does not appear in the network topology",
            details={"slack_bus": slack_bus, "buses": buses},
        )
    missing = set(buses) - set(injections)
    if missing:
        raise ElectricalNetworkError(
            "injections must be supplied for every bus, including the slack bus",
            details={"missing_buses": sorted(missing)},
        )

    reachable = _connected_buses(buses, lines)
    if reachable != set(buses):
        raise ElectricalNetworkError(
            "network graph is not connected (D4 requires a connected topology)",
            details={"disconnected_buses": sorted(set(buses) - reachable)},
        )

    index = {bus: i for i, bus in enumerate(buses)}
    n = len(buses)
    susceptance = np.zeros((n, n))
    for line in lines:
        i, j = index[line.from_bus], index[line.to_bus]
        susceptance[i, i] += line.susceptance
        susceptance[j, j] += line.susceptance
        susceptance[i, j] -= line.susceptance
        susceptance[j, i] -= line.susceptance

    non_slack = [bus for bus in buses if bus != slack_bus]
    reduced_index = [index[bus] for bus in non_slack]
    b_reduced = susceptance[np.ix_(reduced_index, reduced_index)]
    p_reduced = np.array([injections[bus] for bus in non_slack])

    try:
        theta_reduced = np.linalg.solve(b_reduced, p_reduced)
    except np.linalg.LinAlgError as exc:
        raise ElectricalNetworkError(
            f"DC power-flow system is singular: {exc}", details={"buses": buses}
        ) from exc

    angles = {slack_bus: 0.0}
    angles.update(zip(non_slack, (float(theta) for theta in theta_reduced), strict=True))

    flows: list[LineFlow] = []
    outflow: dict[str, float] = {bus: 0.0 for bus in buses}
    for line in lines:
        power = line.susceptance * (angles[line.from_bus] - angles[line.to_bus])
        flows.append(LineFlow(from_bus=line.from_bus, to_bus=line.to_bus, power=power))
        outflow[line.from_bus] += power
        outflow[line.to_bus] -= power

    scale = max((abs(value) for value in injections.values()), default=0.0)
    node_balance = {
        bus: _KCL_LAW.check(
            {"injection": injections[bus], "outflow": outflow[bus]},
            atol=atol,
            rtol=rtol,
            scale=scale,
            unit="pu",
        )
        for bus in buses
    }
    balance = aggregate_balance(node_balance)

    return DcPowerFlowResult(
        slack_bus=slack_bus,
        angles=angles,
        flows=tuple(flows),
        node_balance=node_balance,
        balance=balance,
        assumptions=DC_POWER_FLOW_ASSUMPTIONS,
    )


__all__ = [
    "DC_POWER_FLOW_ASSUMPTIONS",
    "DcPowerFlowResult",
    "ElectricalNetworkError",
    "LineFlow",
    "NetworkLine",
    "dc_power_flow",
]
