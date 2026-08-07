"""Declarative coupling graph (ADR 0028)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from oec.physics.coupling.errors import CouplingGraphError

MANIFEST_VERSION = "coupling_manifest.v0"


class VariableDirection(str, Enum):
    """Direction of an interface variable relative to the edge source."""

    FORWARD = "forward"  # source domain writes; target reads
    BACKWARD = "backward"  # target writes; source reads
    BIDIRECTIONAL = "bidirectional"


@dataclass(frozen=True)
class InterfaceVariable:
    """One exchanged quantity on a coupling edge."""

    var_id: str
    unit: str
    direction: VariableDirection = VariableDirection.FORWARD
    description: str = ""

    def __post_init__(self) -> None:
        if not self.var_id.strip():
            raise CouplingGraphError("InterfaceVariable.var_id must be non-empty")
        if not self.unit.strip():
            raise CouplingGraphError(
                f"InterfaceVariable {self.var_id!r} requires a unit (ADR 0025)"
            )


@dataclass(frozen=True)
class CouplingEdge:
    """Directed coupling between two mono-domain owners."""

    source_domain: str
    target_domain: str
    variables: tuple[InterfaceVariable, ...]
    time_owner: str
    time_consumer: str
    edge_id: str = ""
    conversion_notes: str = ""

    def __post_init__(self) -> None:
        if self.source_domain == self.target_domain:
            raise CouplingGraphError("CouplingEdge cannot connect a domain to itself")
        if not self.variables:
            raise CouplingGraphError("CouplingEdge requires at least one InterfaceVariable")
        if self.time_owner not in (self.source_domain, self.target_domain):
            raise CouplingGraphError(
                f"time_owner {self.time_owner!r} must be source or target domain"
            )
        if self.time_consumer not in (self.source_domain, self.target_domain):
            raise CouplingGraphError(
                f"time_consumer {self.time_consumer!r} must be source or target domain"
            )


@dataclass
class CouplingGraph:
    """Coupling graph with a single simulation clock owner (v0)."""

    edges: list[CouplingEdge] = field(default_factory=list)
    clock_owner: str = ""
    name: str = "coupling_graph"
    manifest_version: str = MANIFEST_VERSION

    def add_edge(self, edge: CouplingEdge) -> None:
        self.edges.append(edge)
        self.validate()

    def domains(self) -> set[str]:
        out: set[str] = set()
        for e in self.edges:
            out.add(e.source_domain)
            out.add(e.target_domain)
        return out

    def validate(self) -> None:
        if not self.edges:
            raise CouplingGraphError("CouplingGraph has no edges")
        domains = self.domains()
        if not self.clock_owner:
            # default: first time_owner seen
            self.clock_owner = self.edges[0].time_owner
        if self.clock_owner not in domains:
            raise CouplingGraphError(
                f"clock_owner {self.clock_owner!r} is not in graph domains {sorted(domains)}"
            )
        # every edge must declare time_owner (already validated on edge)
        write_vars: dict[str, str] = {}
        for e in self.edges:
            for v in e.variables:
                if v.direction in (
                    VariableDirection.FORWARD,
                    VariableDirection.BIDIRECTIONAL,
                ):
                    key = f"{e.source_domain}->{e.target_domain}:{v.var_id}"
                    if key in write_vars:
                        raise CouplingGraphError(f"duplicate interface write path {key}")
                    write_vars[key] = e.source_domain
        # single clock owner rule is structural (one field)

    def to_manifest(self) -> dict[str, Any]:
        self.validate()
        return {
            "manifest_version": self.manifest_version,
            "name": self.name,
            "clock_owner": self.clock_owner,
            "edges": [
                {
                    "edge_id": e.edge_id or f"{e.source_domain}__{e.target_domain}",
                    "source_domain": e.source_domain,
                    "target_domain": e.target_domain,
                    "time_owner": e.time_owner,
                    "time_consumer": e.time_consumer,
                    "conversion_notes": e.conversion_notes,
                    "variables": [
                        {
                            "var_id": v.var_id,
                            "unit": v.unit,
                            "direction": v.direction.value,
                            "description": v.description,
                        }
                        for v in e.variables
                    ],
                }
                for e in self.edges
            ],
        }

    @classmethod
    def from_manifest(cls, data: dict[str, Any]) -> CouplingGraph:
        if data.get("manifest_version") != MANIFEST_VERSION:
            raise CouplingGraphError(
                f"unsupported manifest_version {data.get('manifest_version')!r}"
            )
        edges: list[CouplingEdge] = []
        for raw in data.get("edges") or []:
            variables = tuple(
                InterfaceVariable(
                    var_id=str(v["var_id"]),
                    unit=str(v["unit"]),
                    direction=VariableDirection(str(v.get("direction", "forward"))),
                    description=str(v.get("description") or ""),
                )
                for v in raw.get("variables") or []
            )
            edges.append(
                CouplingEdge(
                    source_domain=str(raw["source_domain"]),
                    target_domain=str(raw["target_domain"]),
                    variables=variables,
                    time_owner=str(raw["time_owner"]),
                    time_consumer=str(raw["time_consumer"]),
                    edge_id=str(raw.get("edge_id") or ""),
                    conversion_notes=str(raw.get("conversion_notes") or ""),
                )
            )
        g = cls(
            edges=edges,
            clock_owner=str(data.get("clock_owner") or ""),
            name=str(data.get("name") or "coupling_graph"),
            manifest_version=str(data.get("manifest_version") or MANIFEST_VERSION),
        )
        g.validate()
        return g
