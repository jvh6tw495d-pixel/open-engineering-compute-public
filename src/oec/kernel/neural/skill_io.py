"""Skill-facing helpers: capacity + runtime + dataset load (Part A complete)."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.runtime import load_xy_from_inputs, runtime_from_skill_inputs
from oec.neural.runtime import CapacityName, resolve_knobs_with_capacity


def _cap(inputs: dict[str, Any]) -> CapacityName | None:
    c = inputs.get("capacity")
    return c if c in ("tiny", "medium", "dense", "wide") else None


def train_sequence_from_inputs(arch: str, inputs: dict[str, Any]) -> dict[str, Any]:
    from oec.kernel.neural.sequences import train_sequence_model

    knobs, capacity = resolve_knobs_with_capacity(
        arch,
        _cap(inputs),
        {
            "hidden": inputs.get("hidden"),
            "n_layers": inputs.get("n_layers"),
            "kernel_size": inputs.get("kernel_size"),
        },
    )
    x, y = load_xy_from_inputs(inputs)
    runtime = runtime_from_skill_inputs(
        inputs,
        default_epochs=int(inputs.get("epochs", 30)),
        default_batch_size=int(inputs.get("batch_size", 8)),
        default_lr=float(inputs.get("lr", 1e-3)),
    )
    return train_sequence_model(
        x,
        y,
        arch=arch,  # type: ignore[arg-type]
        task=str(inputs.get("task", "regression")),  # type: ignore[arg-type]
        n_classes=int(inputs.get("n_classes", 1)),
        hidden=int(knobs["hidden"]),
        n_layers=int(knobs["n_layers"]),
        kernel_size=int(knobs.get("kernel_size", 3)),
        dropout=float(inputs.get("dropout", 0.0)),
        runtime=runtime,
        capacity=capacity,
    )


def train_transformer_from_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    from oec.kernel.neural.transformer import train_transformer_sequence

    knobs, capacity = resolve_knobs_with_capacity(
        "transformer",
        _cap(inputs),
        {
            "d_model": inputs.get("d_model"),
            "n_heads": inputs.get("n_heads"),
            "n_layers": inputs.get("n_layers"),
            "ff_dim": inputs.get("ff_dim"),
        },
    )
    x, y = load_xy_from_inputs(inputs)
    runtime = runtime_from_skill_inputs(
        inputs,
        default_epochs=int(inputs.get("epochs", 25)),
        default_batch_size=int(inputs.get("batch_size", 8)),
        default_lr=float(inputs.get("lr", 1e-3)),
        default_optimizer="adamw",
    )
    return train_transformer_sequence(
        x,
        y,
        task=str(inputs.get("task", "regression")),  # type: ignore[arg-type]
        n_classes=int(inputs.get("n_classes", 1)),
        d_model=int(knobs["d_model"]),
        n_heads=int(knobs["n_heads"]),
        n_layers=int(knobs["n_layers"]),
        ff_dim=int(knobs["ff_dim"]),
        dropout=float(inputs.get("dropout", 0.0)),
        runtime=runtime,
        capacity=capacity,
    )


def train_gnn_from_inputs(arch: str, inputs: dict[str, Any]) -> dict[str, Any]:
    from oec.kernel.neural.gnn import train_gnn

    knobs, capacity = resolve_knobs_with_capacity(
        arch,
        _cap(inputs),
        {
            "hidden": inputs.get("hidden"),
            "n_layers": inputs.get("n_layers"),
            "heads": inputs.get("heads"),
        },
    )
    runtime = runtime_from_skill_inputs(
        inputs,
        default_epochs=int(inputs.get("epochs", 40)),
        default_batch_size=32,
        default_lr=float(inputs.get("lr", 1e-2)),
    )
    return train_gnn(
        inputs["node_features"],
        inputs["edge_index"],
        inputs["y"],
        train_mask=inputs.get("train_mask"),
        arch=arch,  # type: ignore[arg-type]
        task=str(inputs.get("task", "regression")),  # type: ignore[arg-type]
        n_classes=int(inputs.get("n_classes", 1)),
        hidden=int(knobs["hidden"]),
        n_layers=int(knobs["n_layers"]),
        heads=int(knobs.get("heads", 2)),
        dropout=float(inputs.get("dropout", 0.0)),
        runtime=runtime,
        capacity=capacity,
    )


def train_autoencoder_from_inputs(
    inputs: dict[str, Any], *, default_noise: float = 0.0
) -> dict[str, Any]:
    from oec.kernel.neural.autoencoder import train_autoencoder

    knobs, capacity = resolve_knobs_with_capacity(
        "autoencoder",
        _cap(inputs),
        {
            "hidden_dims": inputs.get("hidden_dims"),
            "latent_dim": inputs.get("latent_dim"),
        },
    )
    # x only for AE — optional dataset_path with x.npy only not supported; require x
    if "x" not in inputs and inputs.get("dataset_path"):
        from oec.kernel.neural.runtime import load_dataset_arrays

        x_arr, _ = load_dataset_arrays(
            x=None,
            y=None,
            path=inputs["dataset_path"],
            fmt=str(inputs.get("dataset_format", "npy")),
        )
        # if only x in npz
        x = x_arr.tolist()
    else:
        x = inputs["x"]
    runtime = runtime_from_skill_inputs(
        inputs,
        default_epochs=int(inputs.get("epochs", 40)),
        default_batch_size=int(inputs.get("batch_size", 16)),
        default_lr=float(inputs.get("lr", 1e-3)),
    )
    return train_autoencoder(
        x,
        latent_dim=int(knobs["latent_dim"]),
        hidden_dims=list(knobs["hidden_dims"]),
        noise_std=float(inputs.get("noise_std", default_noise)),
        activation=str(inputs.get("activation", "relu")),
        runtime=runtime,
        capacity=capacity,
    )
