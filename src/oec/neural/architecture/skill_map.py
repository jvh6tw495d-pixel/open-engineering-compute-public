"""Map existing neural skill ids onto ArchitectureGraph (ADR 0047 wave A5).

Declarative only — does not train or change skill numerics. Translates
architectural skill fields onto governed block configs; training keys
(epochs, lr, seed, device, dropout, …) are ignored.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from oec.neural.architecture.errors import ArchitectureValidationError, UnknownBlockError
from oec.neural.architecture.graph import ArchitectureGraph, EdgeGene, NodeGene

_MLP_ACTIVATIONS = frozenset({"relu", "gelu", "silu", "mish", "tanh"})
SkillGraphBuilder = Callable[[dict[str, Any]], ArchitectureGraph]


def graph_for_skill(skill_id: str, inputs: dict[str, Any] | None = None) -> ArchitectureGraph:
    """Return a governed graph for a known neural skill. Unknown ids fail closed."""
    key = str(skill_id).strip()
    builder = _SKILL_GRAPHS.get(key)
    if builder is None:
        raise UnknownBlockError(f"no architecture mapping for skill {key!r}")
    return builder(dict(inputs or {}))


def _chain(nodes: tuple[NodeGene, ...]) -> ArchitectureGraph:
    edges = tuple(
        EdgeGene(source=nodes[i].id, target=nodes[i + 1].id) for i in range(len(nodes) - 1)
    )
    return ArchitectureGraph(nodes=nodes, edges=edges)


def _as_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _infer_vector_width(x: object) -> int | None:
    if not isinstance(x, list) or not x:
        return None
    row = x[0]
    if isinstance(row, list):
        return len(row)
    return None


def _infer_sequence_features(x: object) -> int | None:
    if not isinstance(x, list) or not x:
        return None
    seq = x[0]
    if not isinstance(seq, list) or not seq:
        return None
    step = seq[0]
    if isinstance(step, list):
        return len(step)
    return None


def _infer_conv1d_channels(x: object) -> int | None:
    if not isinstance(x, list) or not x:
        return None
    sample = x[0]
    if isinstance(sample, list):
        return len(sample)
    return None


def _first_hidden_dim(inputs: dict[str, Any], default: int | None) -> int | None:
    if "hidden_dims" in inputs:
        raw = inputs["hidden_dims"]
        if isinstance(raw, list) and raw:
            return _as_int(raw[0])
        return default
    if "hidden" in inputs:
        return _as_int(inputs["hidden"])
    return default


def _map_activation(inputs: dict[str, Any], default: str | None) -> str | None:
    if "activation" not in inputs:
        return default
    raw = inputs["activation"]
    if not isinstance(raw, str):
        raise ArchitectureValidationError(
            f"activation must be str, not {type(raw).__name__}",
            details={"activation": raw},
        )
    if raw not in _MLP_ACTIVATIONS:
        raise ArchitectureValidationError(
            f"activation {raw!r} is not representable in the Architecture IR mlp block",
            details={"activation": raw, "allowed": sorted(_MLP_ACTIVATIONS)},
        )
    return raw


def _mlp(inputs: dict[str, Any], *, classifier: bool) -> ArchitectureGraph:
    cfg: dict[str, Any] = {}
    width = _infer_vector_width(inputs.get("x"))
    if width is not None:
        cfg["in_features"] = width
    hidden = _first_hidden_dim(inputs, 32 if classifier else None)
    if hidden is not None:
        cfg["hidden_dim"] = hidden
    activation = _map_activation(inputs, "relu")
    if activation is not None:
        cfg["activation"] = activation
    if classifier:
        cfg["out_features"] = _as_int(inputs.get("n_classes")) or 2
    else:
        n_classes = _as_int(inputs.get("n_classes"))
        if n_classes is not None:
            cfg["out_features"] = n_classes
        else:
            y = inputs.get("y")
            if (
                isinstance(y, list)
                and y
                and isinstance(y[0], int | float)
                and not isinstance(y[0], bool)
            ):
                cfg["out_features"] = 1
    return ArchitectureGraph(nodes=(NodeGene(id="mlp", block_id="mlp", config=cfg),), edges=())


def _autoencoder(inputs: dict[str, Any]) -> ArchitectureGraph:
    width = _infer_vector_width(inputs.get("x"))
    latent = _as_int(inputs.get("latent_dim")) or 8
    encoder: dict[str, Any] = {"out_features": latent}
    decoder: dict[str, Any] = {"in_features": latent}
    if width is not None:
        encoder["in_features"] = width
        decoder["out_features"] = width
    hidden = _first_hidden_dim(inputs, None)
    if hidden is not None:
        encoder["in_features"] = encoder.get("in_features", hidden)
    return _chain(
        (
            NodeGene(id="encoder", block_id="encoder", config=encoder),
            NodeGene(id="decoder", block_id="decoder", config=decoder),
        )
    )


def _cnn1d(inputs: dict[str, Any]) -> ArchitectureGraph:
    conv: dict[str, Any] = {}
    head: dict[str, Any] = {}
    channels = _infer_conv1d_channels(inputs.get("x"))
    if channels is not None:
        conv["in_channels"] = channels
    hidden = _first_hidden_dim(inputs, 32)
    if hidden is not None:
        conv["out_channels"] = hidden
        head["hidden_dim"] = hidden
        head["in_features"] = hidden
    kernel = _as_int(inputs.get("kernel_size"))
    if kernel is not None:
        conv["kernel_size"] = kernel
    head["out_features"] = _as_int(inputs.get("n_classes")) or 1
    return _chain(
        (
            NodeGene(id="conv", block_id="conv1d", config=conv),
            NodeGene(id="pool", block_id="global_avg_pool_1d"),
            NodeGene(id="head", block_id="mlp", config=head),
        )
    )


def _sequence(inputs: dict[str, Any], block_id: str) -> ArchitectureGraph:
    body: dict[str, Any] = {}
    head: dict[str, Any] = {}
    features = _infer_sequence_features(inputs.get("x"))
    hidden = _first_hidden_dim(inputs, 32)
    n_layers = _as_int(inputs.get("n_layers"))
    if block_id in {"lstm", "gru"}:
        if features is not None:
            body["input_size"] = features
        if hidden is not None:
            body["hidden_dim"] = hidden
            head["hidden_dim"] = hidden
            head["in_features"] = hidden
        body["n_layers"] = n_layers or 1
    elif block_id == "tcn":
        if hidden is not None:
            body["hidden_dim"] = hidden
            head["hidden_dim"] = hidden
            head["in_features"] = hidden
        body["n_layers"] = n_layers or 1
        kernel = _as_int(inputs.get("kernel_size"))
        if kernel is not None:
            body["kernel_size"] = kernel
    elif block_id == "transformer_encoder":
        d_model = _as_int(inputs.get("d_model")) or 32
        nhead = _as_int(inputs.get("n_heads")) or 4
        ff_dim = _as_int(inputs.get("ff_dim")) or 64
        layers = n_layers or 2
        if nhead > 0 and d_model % nhead != 0:
            raise ArchitectureValidationError(
                "transformer d_model must be divisible by n_heads",
                details={"d_model": d_model, "n_heads": nhead},
            )
        body["d_model"] = d_model
        body["nhead"] = nhead
        body["num_layers"] = layers
        body["dim_feedforward"] = ff_dim
        head["in_features"] = d_model
        head["hidden_dim"] = d_model
    head["out_features"] = _as_int(inputs.get("n_classes")) or 1
    return _chain(
        (
            NodeGene(id="body", block_id=block_id, config=body),
            NodeGene(id="pool", block_id="sequence_pool"),
            NodeGene(id="head", block_id="mlp", config=head),
        )
    )


def _gnn(inputs: dict[str, Any], block_id: str) -> ArchitectureGraph:
    body: dict[str, Any] = {}
    head: dict[str, Any] = {}
    hidden = _first_hidden_dim(inputs, 16)
    if hidden is not None:
        body["hidden_dim"] = hidden
        head["hidden_dim"] = hidden
        head["in_features"] = hidden
    body["n_layers"] = _as_int(inputs.get("n_layers")) or 2
    heads = _as_int(inputs.get("heads"))
    if heads is not None and block_id == "gat":
        body["heads"] = heads
    width = _infer_vector_width(inputs.get("node_features"))
    if width is not None:
        head["in_features"] = hidden or width
    head["out_features"] = _as_int(inputs.get("n_classes")) or 1
    return _chain(
        (
            NodeGene(id="gnn", block_id=block_id, config=body),
            NodeGene(id="pool", block_id="graph_global_pool"),
            NodeGene(id="to_vec", block_id="graph_embedding_to_vector"),
            NodeGene(id="head", block_id="mlp", config=head),
        )
    )


_SKILL_GRAPHS: dict[str, SkillGraphBuilder] = {
    "neural.mlp.regressor": lambda inputs: _mlp(inputs, classifier=False),
    "neural.mlp.classifier": lambda inputs: _mlp(inputs, classifier=True),
    "neural.autoencoder.basic": _autoencoder,
    "neural.autoencoder.denoising": _autoencoder,
    "neural.cnn1d": _cnn1d,
    "neural.lstm": lambda inputs: _sequence(inputs, "lstm"),
    "neural.gru": lambda inputs: _sequence(inputs, "gru"),
    "neural.tcn": lambda inputs: _sequence(inputs, "tcn"),
    "neural.transformer.encoder": lambda inputs: _sequence(inputs, "transformer_encoder"),
    "neural.transformer.sequence_regressor": lambda inputs: _sequence(
        inputs, "transformer_encoder"
    ),
    "neural.transformer.sequence_classifier": lambda inputs: _sequence(
        inputs, "transformer_encoder"
    ),
    "neural.gcn": lambda inputs: _gnn(inputs, "gcn"),
    "neural.graphsage": lambda inputs: _gnn(inputs, "graphsage"),
    "neural.gat": lambda inputs: _gnn(inputs, "gat"),
}


def mapped_skill_ids() -> tuple[str, ...]:
    return tuple(sorted(_SKILL_GRAPHS))
