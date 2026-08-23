"""Governed Neural Architecture IR (ADR 0047). Importable without torch."""

from __future__ import annotations

from oec.neural.architecture.compatibility import check_connection
from oec.neural.architecture.default_catalog import default_registry, make_default_registry
from oec.neural.architecture.errors import (
    ArchitectureValidationError,
    DuplicateBlockError,
    RegistrySealedError,
    UnknownBlockError,
    UnknownFamilyError,
)
from oec.neural.architecture.governance import (
    COMPATIBILITY_VERSION,
    ArchitectureManifest,
    ArchitectureProvenance,
    CatalogAuditReport,
    audit_catalog,
    manifest_for_graph,
    validate_for_backend,
)
from oec.neural.architecture.graph import (
    ArchitectureGraph,
    ArchitectureValidationReport,
    EdgeGene,
    NodeGene,
)
from oec.neural.architecture.operators import crossover_graphs, mutate_graph
from oec.neural.architecture.registry import BlockRegistry
from oec.neural.architecture.search import search_graphs
from oec.neural.architecture.skill_map import graph_for_skill, mapped_skill_ids
from oec.neural.architecture.specs import BlockParameterSpec, BlockSpec, CompatibilityResult
from oec.neural.architecture.taxonomy import ArchitectureActivationName, MotifName
from oec.neural.architecture.types import BlockCategory, NeuralFamily, TensorKind

__all__ = [
    "COMPATIBILITY_VERSION",
    "ArchitectureActivationName",
    "ArchitectureGraph",
    "ArchitectureManifest",
    "ArchitectureProvenance",
    "ArchitectureValidationError",
    "ArchitectureValidationReport",
    "BlockCategory",
    "BlockParameterSpec",
    "BlockRegistry",
    "BlockSpec",
    "CatalogAuditReport",
    "CompatibilityResult",
    "DuplicateBlockError",
    "EdgeGene",
    "MotifName",
    "NeuralFamily",
    "NodeGene",
    "RegistrySealedError",
    "TensorKind",
    "UnknownBlockError",
    "UnknownFamilyError",
    "audit_catalog",
    "check_connection",
    "crossover_graphs",
    "default_registry",
    "graph_for_skill",
    "make_default_registry",
    "manifest_for_graph",
    "mapped_skill_ids",
    "mutate_graph",
    "search_graphs",
    "validate_for_backend",
]
