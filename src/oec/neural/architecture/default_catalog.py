"""Default governed block catalog v0.1.0 (ADR 0047). Declarative only."""

from __future__ import annotations

from oec.neural.architecture.adapters import ADAPTER_SPECS
from oec.neural.architecture.registry import BlockRegistry
from oec.neural.architecture.specs import BlockParameterSpec, BlockSpec
from oec.neural.architecture.types import BlockCategory, NeuralFamily, TensorKind

BASE_BLOCKS = (
    BlockSpec(
        id="linear",
        display_name="Linear",
        family=NeuralFamily.FEEDFORWARD,
        category=BlockCategory.PRIMITIVE,
        input_kinds=frozenset({TensorKind.VECTOR}),
        output_kind=TensorKind.VECTOR,
        parameters=(
            BlockParameterSpec(name="out_features", kind="int", required=True, minimum=1),
            BlockParameterSpec(name="bias", kind="bool", default=True),
        ),
        capabilities=frozenset({"dense", "projection"}),
        experimental=False,
    ),
    BlockSpec(
        id="mlp",
        display_name="MLP Block",
        family=NeuralFamily.FEEDFORWARD,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.VECTOR}),
        output_kind=TensorKind.VECTOR,
        parameters=(
            BlockParameterSpec(name="hidden_dim", kind="int", default=128, minimum=8),
            BlockParameterSpec(
                name="activation",
                kind="enum",
                default="gelu",
                choices=("relu", "gelu", "silu", "mish", "tanh"),
            ),
        ),
        capabilities=frozenset({"dense"}),
        experimental=False,
    ),
    BlockSpec(
        id="residual_mlp",
        display_name="Residual MLP",
        family=NeuralFamily.FEEDFORWARD,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.VECTOR}),
        output_kind=TensorKind.VECTOR,
        capabilities=frozenset({"dense", "residual"}),
    ),
    BlockSpec(
        id="swiglu",
        display_name="SwiGLU",
        family=NeuralFamily.FEEDFORWARD,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.VECTOR, TensorKind.SEQUENCE}),
        output_kind=TensorKind.VECTOR,
        parameters=(BlockParameterSpec(name="hidden_dim", kind="int", default=128, minimum=8),),
        capabilities=frozenset({"gated"}),
    ),
    BlockSpec(
        id="conv1d",
        display_name="Conv1D Block",
        family=NeuralFamily.CONVOLUTIONAL,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.IMAGE_1D, TensorKind.FEATURE_MAP_1D}),
        output_kind=TensorKind.FEATURE_MAP_1D,
        capabilities=frozenset({"local_receptive_field"}),
        experimental=False,
    ),
    BlockSpec(
        id="conv2d",
        display_name="Conv2D Block",
        family=NeuralFamily.CONVOLUTIONAL,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.IMAGE_2D, TensorKind.FEATURE_MAP_2D}),
        output_kind=TensorKind.FEATURE_MAP_2D,
        capabilities=frozenset({"local_receptive_field"}),
    ),
    BlockSpec(
        id="lstm",
        display_name="LSTM",
        family=NeuralFamily.RECURRENT,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.SEQUENCE}),
        output_kind=TensorKind.SEQUENCE,
        capabilities=frozenset({"recurrent", "gated"}),
        experimental=False,
    ),
    BlockSpec(
        id="gru",
        display_name="GRU",
        family=NeuralFamily.RECURRENT,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.SEQUENCE}),
        output_kind=TensorKind.SEQUENCE,
        capabilities=frozenset({"recurrent", "gated"}),
        experimental=False,
    ),
    BlockSpec(
        id="tcn",
        display_name="Temporal Convolutional Network Block",
        family=NeuralFamily.CONVOLUTIONAL,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.SEQUENCE}),
        output_kind=TensorKind.SEQUENCE,
        capabilities=frozenset({"temporal", "dilated_conv"}),
        experimental=False,
    ),
    BlockSpec(
        id="self_attention",
        display_name="Self Attention",
        family=NeuralFamily.ATTENTION,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.SEQUENCE}),
        output_kind=TensorKind.SEQUENCE,
        capabilities=frozenset({"attention"}),
    ),
    BlockSpec(
        id="transformer_encoder",
        display_name="Transformer Encoder",
        family=NeuralFamily.TRANSFORMER,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.SEQUENCE}),
        output_kind=TensorKind.SEQUENCE,
        capabilities=frozenset({"attention", "residual", "feedforward"}),
        experimental=False,
    ),
    BlockSpec(
        id="kan",
        display_name="KAN Block",
        family=NeuralFamily.KAN,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.VECTOR}),
        output_kind=TensorKind.VECTOR,
        parameters=(
            BlockParameterSpec(
                name="basis",
                kind="enum",
                default="bspline",
                choices=("bspline", "rbf"),
            ),
            BlockParameterSpec(name="grid_size", kind="int", default=8, minimum=2, maximum=128),
        ),
        capabilities=frozenset({"functional_edges"}),
        backend_requirements=("future-kan-backend",),
        experimental=True,
        notes="Declarative catalog entry only in IR v0.1.",
    ),
    BlockSpec(
        id="gcn",
        display_name="Graph Convolutional Network",
        family=NeuralFamily.GRAPH,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.GRAPH, TensorKind.NODE_FEATURES}),
        output_kind=TensorKind.NODE_FEATURES,
        capabilities=frozenset({"message_passing"}),
        experimental=False,
    ),
    BlockSpec(
        id="graphsage",
        display_name="GraphSAGE",
        family=NeuralFamily.GRAPH,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.GRAPH, TensorKind.NODE_FEATURES}),
        output_kind=TensorKind.NODE_FEATURES,
        capabilities=frozenset({"message_passing", "aggregation"}),
        experimental=False,
    ),
    BlockSpec(
        id="gat",
        display_name="Graph Attention Network",
        family=NeuralFamily.GRAPH,
        category=BlockCategory.BLOCK,
        input_kinds=frozenset({TensorKind.GRAPH, TensorKind.NODE_FEATURES}),
        output_kind=TensorKind.NODE_FEATURES,
        capabilities=frozenset({"message_passing", "attention"}),
        experimental=False,
    ),
    BlockSpec(
        id="encoder",
        display_name="Encoder Motif",
        family=NeuralFamily.AUTOENCODER,
        category=BlockCategory.MOTIF,
        input_kinds=frozenset({TensorKind.VECTOR}),
        output_kind=TensorKind.LATENT,
        capabilities=frozenset({"representation_learning"}),
        experimental=False,
    ),
    BlockSpec(
        id="decoder",
        display_name="Decoder Motif",
        family=NeuralFamily.AUTOENCODER,
        category=BlockCategory.MOTIF,
        input_kinds=frozenset({TensorKind.LATENT}),
        output_kind=TensorKind.VECTOR,
        capabilities=frozenset({"reconstruction"}),
        experimental=False,
    ),
)


def make_default_registry() -> BlockRegistry:
    registry = BlockRegistry(version="0.1.0")
    registry.register_many(BASE_BLOCKS)
    registry.register_many(ADAPTER_SPECS)
    return registry


default_registry = make_default_registry()
