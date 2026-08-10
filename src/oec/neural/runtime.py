"""Shared dense neural runtime contracts (Part A / N-D0).

No torch import — safe in core installs. Capacity tables and runtime knobs
are closed enums / caps only (ADR 0031).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from oec.neural.contracts import DeviceSpec, OptimizerSpec

CapacityName = Literal["tiny", "medium", "dense", "wide"]
NeuralFamily = Literal["mlp", "sequence", "transformer", "gnn", "autoencoder"]
CheckpointStorage = Literal["json_inline", "file"]
DatasetFormat = Literal["json_inline", "npy", "parquet"]
LrSchedulerName = Literal["none", "cosine", "step"]

# ---------------------------------------------------------------------------
# Capacity tables (Part A.5) — closed, versioned by this module
# ---------------------------------------------------------------------------

_MLP_CAPACITY: dict[str, dict[str, Any]] = {
    "tiny": {"hidden_dims": [64, 32]},
    "medium": {"hidden_dims": [256, 256, 128]},
    "dense": {"hidden_dims": [512, 512, 256, 128]},
    "wide": {"hidden_dims": [1024, 512, 256]},
}

_SEQUENCE_CAPACITY: dict[str, dict[str, Any]] = {
    "tiny": {"hidden": 32, "n_layers": 1, "kernel_size": 3},
    "medium": {"hidden": 128, "n_layers": 2, "kernel_size": 5},
    "dense": {"hidden": 256, "n_layers": 3, "kernel_size": 5},
    "wide": {"hidden": 512, "n_layers": 2, "kernel_size": 7},
}

_TRANSFORMER_CAPACITY: dict[str, dict[str, Any]] = {
    "tiny": {"d_model": 64, "n_heads": 4, "n_layers": 2, "ff_dim": 128},
    "medium": {"d_model": 128, "n_heads": 4, "n_layers": 3, "ff_dim": 256},
    "dense": {"d_model": 256, "n_heads": 8, "n_layers": 4, "ff_dim": 512},
    "wide": {"d_model": 384, "n_heads": 8, "n_layers": 3, "ff_dim": 768},
}

_GNN_CAPACITY: dict[str, dict[str, Any]] = {
    "tiny": {"hidden": 32, "n_layers": 2, "heads": 2},
    "medium": {"hidden": 64, "n_layers": 3, "heads": 4},
    "dense": {"hidden": 128, "n_layers": 3, "heads": 4},
    "wide": {"hidden": 256, "n_layers": 2, "heads": 8},
}

_AUTOENCODER_CAPACITY: dict[str, dict[str, Any]] = {
    "tiny": {"hidden_dims": [32], "latent_dim": 8},
    "medium": {"hidden_dims": [128, 64], "latent_dim": 16},
    "dense": {"hidden_dims": [256, 128, 64], "latent_dim": 32},
    "wide": {"hidden_dims": [512, 256], "latent_dim": 64},
}

_CAPACITY_BY_FAMILY: dict[str, dict[str, dict[str, Any]]] = {
    "mlp": _MLP_CAPACITY,
    "sequence": _SEQUENCE_CAPACITY,
    "transformer": _TRANSFORMER_CAPACITY,
    "gnn": _GNN_CAPACITY,
    "autoencoder": _AUTOENCODER_CAPACITY,
}

# Map skill/arch names → family for resolve_capacity convenience
_ARCH_TO_FAMILY: dict[str, NeuralFamily] = {
    "mlp": "mlp",
    "mlp_bn": "mlp",
    "mlp_residual": "mlp",
    "cnn1d": "sequence",
    "lstm": "sequence",
    "gru": "sequence",
    "tcn": "sequence",
    "transformer": "transformer",
    "transformer_encoder": "transformer",
    "gcn": "gnn",
    "graphsage": "gnn",
    "gat": "gnn",
    "autoencoder": "autoencoder",
}


def resolve_capacity(
    family_or_arch: str,
    capacity: CapacityName,
) -> dict[str, Any]:
    """Expand a capacity preset into architecture knobs.

    ``family_or_arch`` may be a family name (``mlp``, ``sequence``, …) or a
    concrete architecture id (``lstm``, ``gcn``, …).
    """
    family: str
    if family_or_arch in _CAPACITY_BY_FAMILY:
        family = family_or_arch
    elif family_or_arch in _ARCH_TO_FAMILY:
        family = _ARCH_TO_FAMILY[family_or_arch]
    else:
        raise ValueError(
            f"unknown neural family/architecture {family_or_arch!r}; "
            f"choose from {sorted(set(_CAPACITY_BY_FAMILY) | set(_ARCH_TO_FAMILY))}"
        )
    table = _CAPACITY_BY_FAMILY[family]
    if capacity not in table:
        raise ValueError(f"unknown capacity {capacity!r}; choose from tiny|medium|dense|wide")
    # Return a shallow copy so callers can mutate safely
    return dict(table[capacity])


def resolve_mlp_hidden_dims(
    *,
    capacity: CapacityName | None,
    hidden_dims: list[int] | None,
) -> tuple[list[int], CapacityName | None]:
    """Apply Part A.5 precedence: raw ``hidden_dims`` wins if provided.

    Returns ``(hidden_dims, capacity_used)`` where ``capacity_used`` is None
    when raw knobs were supplied.
    """
    if hidden_dims is not None and len(hidden_dims) > 0:
        return list(hidden_dims), None
    cap: CapacityName = capacity or "tiny"
    resolved = resolve_capacity("mlp", cap)
    return list(resolved["hidden_dims"]), cap


def resolve_knobs_with_capacity(
    family_or_arch: str,
    capacity: CapacityName | None,
    overrides: dict[str, Any],
) -> tuple[dict[str, Any], CapacityName | None]:
    """Merge capacity preset with raw overrides (overrides win per key).

    If any override key is present and non-None, that key is not taken from
    the preset. If *no* capacity and no overrides, uses ``tiny``.
    Returns ``(knobs, capacity_used)`` — capacity_used is None when the
    caller fully specified all preset keys via overrides.
    """
    table_keys = set(resolve_capacity(family_or_arch, "tiny").keys())
    provided = {k: v for k, v in overrides.items() if v is not None and k in table_keys}
    if capacity is None and provided:
        # partial raw knobs: fill missing from tiny
        base = resolve_capacity(family_or_arch, "tiny")
        base.update(provided)
        return base, None if provided.keys() >= table_keys else "tiny"
    cap: CapacityName = capacity or "tiny"
    base = resolve_capacity(family_or_arch, cap)
    base.update(provided)
    used: CapacityName | None = None if provided.keys() >= table_keys else cap
    return base, used


def estimate_mlp_param_count(
    input_dim: int,
    hidden_dims: list[int],
    output_dim: int = 1,
) -> int:
    """Closed-form Linear+bias parameter count (no torch required)."""
    dims = [input_dim, *hidden_dims, output_dim]
    total = 0
    for a, b in zip(dims[:-1], dims[1:], strict=True):
        total += a * b + b
    return total


class TrainingRuntimeSpec(BaseModel):
    """Shared train-loop knobs for all neural families (Part A.3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    seed: int = 42
    device: DeviceSpec = Field(default_factory=DeviceSpec)
    epochs: int = Field(default=100, ge=1, le=10_000)
    batch_size: int = Field(default=32, ge=1, le=65_536)
    optimizer: OptimizerSpec = Field(default_factory=OptimizerSpec)
    lr_scheduler: LrSchedulerName = "none"
    step_size: int = Field(default=50, ge=1)
    grad_clip: float | None = Field(default=None, gt=0.0)
    amp: bool = False
    early_stopping_patience: int | None = Field(default=20, ge=1)
    max_params: int = Field(default=5_000_000, ge=1_000, le=50_000_000)
    max_seconds: float | None = Field(default=None, gt=0.0)
    checkpoint_storage: CheckpointStorage = "json_inline"

    @model_validator(mode="after")
    def _amp_device(self) -> TrainingRuntimeSpec:
        # Soft rule documented: amp on pure cpu is invalid at skill validation.
        # We allow the model to construct; kernel raises if amp requested without CUDA.
        return self


class DatasetRef(BaseModel):
    """Inline arrays or path reference (Part A.4). N-D3 path load is kernel-side."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    x: list[Any] | None = None
    y: list[Any] | None = None
    path: str | None = None
    format: DatasetFormat = "json_inline"
    val_fraction: float = Field(default=0.2, ge=0.0, lt=1.0)

    @model_validator(mode="after")
    def _mode(self) -> DatasetRef:
        if self.format == "json_inline":
            if self.x is None or self.y is None:
                raise ValueError("json_inline DatasetRef requires x and y")
            if len(self.x) < 2 or len(self.y) < 2:
                raise ValueError("dataset must have at least 2 rows")
            if len(self.x) != len(self.y):
                raise ValueError("x and y length mismatch")
        else:
            if not self.path:
                raise ValueError(f"format={self.format!r} requires path")
        return self


class CheckpointRef(BaseModel):
    """Where weights live after training (Part A.4)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    storage: CheckpointStorage = "json_inline"
    path: str | None = None
    sha256: str | None = None
    format_version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def _file_fields(self) -> CheckpointRef:
        if self.storage == "file" and (not self.path or not self.sha256):
            raise ValueError("file CheckpointRef requires path and sha256")
        return self
