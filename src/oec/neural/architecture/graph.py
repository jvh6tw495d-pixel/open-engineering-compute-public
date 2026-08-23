"""Architecture graph IR — DAG of governed blocks (ADR 0047)."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, GetCoreSchemaHandler
from pydantic_core import core_schema

from oec.neural.architecture.compatibility import check_connection
from oec.neural.architecture.errors import (
    ArchitectureValidationError,
    UnknownBlockError,
)
from oec.neural.architecture.registry import BlockRegistry

ARCHITECTURE_COMPATIBILITY_VERSION = "1.0"


class FrozenConfig(dict[str, Any]):
    """JSON-finite node config that rejects in-place mutation."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.dict_schema(
                keys_schema=core_schema.str_schema(),
                values_schema=core_schema.any_schema(),
            ),
        )

    @classmethod
    def _validate(cls, value: dict[str, Any]) -> FrozenConfig:
        try:
            return cls(_json_finite_object(value))
        except ArchitectureValidationError as exc:
            raise ValueError(exc.message) from exc

    def __setitem__(self, key: str, value: Any) -> None:
        raise TypeError("architecture node config is immutable")

    def __delitem__(self, key: str) -> None:
        raise TypeError("architecture node config is immutable")

    def clear(self) -> None:
        raise TypeError("architecture node config is immutable")

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError("architecture node config is immutable")

    def popitem(self) -> Any:
        raise TypeError("architecture node config is immutable")

    def update(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("architecture node config is immutable")

    def setdefault(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError("architecture node config is immutable")


class NodeGene(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    block_id: str
    config: FrozenConfig = Field(default_factory=FrozenConfig)


class EdgeGene(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str
    target: str
    source_port: str = "out"
    target_port: str = "in"


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

        incident = {node_id: 0 for node_id in node_map}
        for edge in self.edges:
            if edge.source in incident:
                incident[edge.source] += 1
            if edge.target in incident:
                incident[edge.target] += 1
        if len(node_map) > 1:
            for node_id, count in incident.items():
                if count == 0:
                    errors.append(f"orphan node: {node_id}")

        for node in self.nodes:
            try:
                spec = registry.get(node.block_id)
            except UnknownBlockError:
                errors.append(f"unknown block: {node.block_id}")
                continue
            if spec.experimental:
                warnings.append(f"experimental block: {node.block_id}")
            try:
                spec.validate_config(dict(node.config))
            except ArchitectureValidationError as exc:
                errors.append(exc.message)

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
            if edge.source_port not in source_spec.output_ports:
                errors.append(
                    f"edge {edge.source}->{edge.target} has unknown source_port "
                    f"{edge.source_port!r}; block {source_spec.id!r} declares "
                    f"output_ports={list(source_spec.output_ports)}"
                )
            result = check_connection(source_spec, target_spec, registry)
            if not result.compatible:
                suffix = ""
                if result.suggested_adapters:
                    suffix = f"; suggested adapters={list(result.suggested_adapters)}"
                errors.append(
                    f"incompatible edge {edge.source}->{edge.target}: {result.reason}{suffix}"
                )

        errors.extend(self._port_wiring_errors(node_map, registry))

        if not self._is_dag():
            errors.append("architecture graph is not a valid DAG")

        return ArchitectureValidationReport(
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(sorted(set(warnings))),
        )

    def _port_wiring_errors(
        self, node_map: dict[str, NodeGene], registry: BlockRegistry
    ) -> list[str]:
        """Every declared input port of a target node must be wired exactly once.

        A node with zero incoming edges and a single ("in") port is a graph
        root that receives its tensor from outside the graph, so it is exempt.
        A node with arity > 1 (named joins, e.g. cross_attention) is never
        exempt: all of its ports must come from graph edges.
        """
        incoming: dict[str, list[EdgeGene]] = {}
        for edge in self.edges:
            incoming.setdefault(edge.target, []).append(edge)

        errors: list[str] = []
        for node_id, node in node_map.items():
            try:
                spec = registry.get(node.block_id)
            except UnknownBlockError:
                continue
            expected_ports = spec.input_ports
            edges_in = incoming.get(node_id, [])
            if not edges_in and len(expected_ports) <= 1:
                continue
            port_counts: dict[str, int] = {}
            for edge in edges_in:
                port_counts[edge.target_port] = port_counts.get(edge.target_port, 0) + 1
            missing = [port for port in expected_ports if port not in port_counts]
            extra = sorted(port for port in port_counts if port not in expected_ports)
            duplicate = sorted(
                port for port, count in port_counts.items() if count > 1 and port in expected_ports
            )
            if missing:
                errors.append(f"node {node_id} is missing wiring for ports {missing}")
            if extra:
                errors.append(f"node {node_id} has edges to unknown ports {extra}")
            if duplicate:
                errors.append(f"node {node_id} has ports wired more than once: {duplicate}")
        return errors

    def canonical_dict(self, registry: BlockRegistry | None = None) -> dict[str, Any]:
        if registry is None:
            from oec.neural.architecture.default_catalog import default_registry

            registry = default_registry
        nodes: list[dict[str, Any]] = []
        for node in sorted(self.nodes, key=lambda item: item.id):
            config = _json_finite_object(dict(node.config))
            try:
                spec = registry.get(node.block_id)
                config = _json_finite_object(spec.validate_config(config))
            except (UnknownBlockError, ArchitectureValidationError):
                pass
            nodes.append({"id": node.id, "block_id": node.block_id, "config": config})
        return {
            "version": self.version,
            "compatibility_version": ARCHITECTURE_COMPATIBILITY_VERSION,
            "registry_version": registry.version,
            "catalog_hash": registry.catalog_hash(),
            "nodes": nodes,
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "source_port": edge.source_port,
                    "target_port": edge.target_port,
                }
                for edge in sorted(
                    self.edges,
                    key=lambda item: (item.source, item.target, item.source_port, item.target_port),
                )
            ],
        }

    def fingerprint(self, registry: BlockRegistry | None = None) -> str:
        payload = json.dumps(
            self.canonical_dict(registry),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def _json_finite_object(value: dict[str, Any]) -> dict[str, Any]:
    canonical = _json_finite_value(value)
    if not isinstance(canonical, dict):
        raise ArchitectureValidationError("architecture config must be a JSON object")
    return canonical


def _json_finite_value(value: object) -> Any:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ArchitectureValidationError("non-finite float in architecture config")
        return value
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value, key=str):
            if not isinstance(key, str):
                raise ArchitectureValidationError(
                    f"config keys must be str, not {type(key).__name__}"
                )
            out[key] = _json_finite_value(value[key])
        return out
    if isinstance(value, (list, tuple)):
        return [_json_finite_value(item) for item in value]
    raise ArchitectureValidationError(
        f"non-JSON config value: {type(value).__name__}",
        details={"type": type(value).__name__},
    )
