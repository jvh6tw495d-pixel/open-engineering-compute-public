"""Architecture graph IR — DAG of governed blocks (ADR 0047)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from oec.neural.architecture.compatibility import check_connection
from oec.neural.architecture.errors import (
    ArchitectureValidationError,
    UnknownBlockError,
)
from oec.neural.architecture.registry import BlockRegistry


class NodeGene(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    block_id: str
    config: dict[str, Any] = Field(default_factory=dict)


class EdgeGene(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str
    target: str


class ArchitectureValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class ArchitectureGraph(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    nodes: tuple[NodeGene, ...]
    edges: tuple[EdgeGene, ...] = ()
    version: str = "0.1"

    def _node_map(self) -> dict[str, NodeGene]:
        mapping: dict[str, NodeGene] = {}
        for node in self.nodes:
            if node.id in mapping:
                raise ArchitectureValidationError(f"duplicate node id: {node.id}")
            mapping[node.id] = node
        return mapping

    def _is_dag(self) -> bool:
        try:
            node_map = self._node_map()
        except ArchitectureValidationError:
            return False
        indegree = {node_id: 0 for node_id in node_map}
        adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_map}
        for edge in self.edges:
            if edge.source not in node_map or edge.target not in node_map:
                return False
            adjacency[edge.source].append(edge.target)
            indegree[edge.target] += 1
        queue = [node_id for node_id, degree in indegree.items() if degree == 0]
        seen = 0
        while queue:
            current = queue.pop()
            seen += 1
            for nxt in adjacency[current]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)
        return seen == len(node_map)

    def validate_graph(self, registry: BlockRegistry) -> ArchitectureValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        try:
            node_map = self._node_map()
        except ArchitectureValidationError as exc:
            return ArchitectureValidationReport(valid=False, errors=(exc.message,), warnings=())

        for node in self.nodes:
            try:
                spec = registry.get(node.block_id)
            except UnknownBlockError:
                errors.append(f"unknown block: {node.block_id}")
                continue
            if spec.experimental:
                warnings.append(f"experimental block: {node.block_id}")

        for edge in self.edges:
            if edge.source not in node_map:
                errors.append(f"unknown source node: {edge.source}")
                continue
            if edge.target not in node_map:
                errors.append(f"unknown target node: {edge.target}")
                continue
            try:
                source_spec = registry.get(node_map[edge.source].block_id)
                target_spec = registry.get(node_map[edge.target].block_id)
            except UnknownBlockError:
                continue
            result = check_connection(source_spec, target_spec, registry)
            if not result.compatible:
                suffix = ""
                if result.suggested_adapters:
                    suffix = f"; suggested adapters={list(result.suggested_adapters)}"
                errors.append(
                    f"incompatible edge {edge.source}->{edge.target}: {result.reason}{suffix}"
                )

        if not self._is_dag():
            errors.append("architecture graph is not a valid DAG")

        return ArchitectureValidationReport(
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(sorted(set(warnings))),
        )

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "nodes": [
                {"id": node.id, "block_id": node.block_id, "config": node.config}
                for node in sorted(self.nodes, key=lambda item: item.id)
            ],
            "edges": [
                {"source": edge.source, "target": edge.target}
                for edge in sorted(self.edges, key=lambda item: (item.source, item.target))
            ],
        }

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
