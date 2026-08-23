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
from oec.neural.architecture.graph import (
    ArchitectureGraph,
    ArchitectureValidationReport,
    EdgeGene,
    NodeGene,
)
from oec.neural.architecture.registry import BlockRegistry
from oec.neural.architecture.skill_map import graph_for_skill, mapped_skill_ids
from oec.neural.architecture.specs import BlockParameterSpec, BlockSpec, CompatibilityResult
from oec.neural.architecture.taxonomy import ArchitectureActivationName, MotifName
from oec.neural.architecture.types import BlockCategory, NeuralFamily, TensorKind

__all__ = [
    "ArchitectureActivationName",
    "ArchitectureGraph",
    "ArchitectureValidationError",
    "ArchitectureValidationReport",
    "BlockCategory",
    "BlockParameterSpec",
    "BlockRegistry",
    "BlockSpec",
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
    "check_connection",
    "default_registry",
    "graph_for_skill",
    "make_default_registry",
    "mapped_skill_ids",
]
