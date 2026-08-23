"""Explicit shape adapters — never implicit reshape (ADR 0047)."""

from __future__ import annotations

from oec.neural.architecture.specs import BlockSpec
from oec.neural.architecture.types import BlockCategory, NeuralFamily, TensorKind

ADAPTER_SPECS = (
    BlockSpec(
        id="flatten",
        display_name="Flatten",
        family=NeuralFamily.STRUCTURAL,
        category=BlockCategory.ADAPTER,
        input_kinds=frozenset(
            {
                TensorKind.FEATURE_MAP_1D,
                TensorKind.FEATURE_MAP_2D,
                TensorKind.FEATURE_MAP_3D,
            }
        ),
        output_kind=TensorKind.VECTOR,
        capabilities=frozenset({"shape_transform"}),
        experimental=False,
    ),
    BlockSpec(
        id="global_avg_pool_1d",
        display_name="Global Average Pool 1D",
        family=NeuralFamily.STRUCTURAL,
        category=BlockCategory.ADAPTER,
        input_kinds=frozenset({TensorKind.FEATURE_MAP_1D}),
        output_kind=TensorKind.VECTOR,
        experimental=False,
    ),
    BlockSpec(
        id="global_avg_pool_2d",
        display_name="Global Average Pool 2D",
        family=NeuralFamily.STRUCTURAL,
        category=BlockCategory.ADAPTER,
        input_kinds=frozenset({TensorKind.FEATURE_MAP_2D}),
        output_kind=TensorKind.VECTOR,
        experimental=False,
    ),
    BlockSpec(
        id="sequence_pool",
        display_name="Sequence Pool",
        family=NeuralFamily.STRUCTURAL,
        category=BlockCategory.ADAPTER,
        input_kinds=frozenset({TensorKind.SEQUENCE}),
        output_kind=TensorKind.VECTOR,
        experimental=False,
    ),
    BlockSpec(
        id="vector_to_sequence",
        display_name="Vector To Sequence Projection",
        family=NeuralFamily.STRUCTURAL,
        category=BlockCategory.ADAPTER,
        input_kinds=frozenset({TensorKind.VECTOR}),
        output_kind=TensorKind.SEQUENCE,
        experimental=False,
    ),
    BlockSpec(
        id="graph_global_pool",
        display_name="Graph Global Pool",
        family=NeuralFamily.STRUCTURAL,
        category=BlockCategory.ADAPTER,
        input_kinds=frozenset({TensorKind.NODE_FEATURES}),
        output_kind=TensorKind.GRAPH_EMBEDDING,
        experimental=False,
    ),
    BlockSpec(
        id="graph_embedding_to_vector",
        display_name="Graph Embedding To Vector",
        family=NeuralFamily.STRUCTURAL,
        category=BlockCategory.ADAPTER,
        input_kinds=frozenset({TensorKind.GRAPH_EMBEDDING}),
        output_kind=TensorKind.VECTOR,
        experimental=False,
    ),
)
