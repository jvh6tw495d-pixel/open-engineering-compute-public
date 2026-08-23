"""Architecture-IR activation and motif names (ADR 0047).

Distinct from ``oec.neural.contracts.ActivationName`` (training knobs).
"""

from __future__ import annotations

from enum import StrEnum


class ArchitectureActivationName(StrEnum):
    RELU = "relu"
    LEAKY_RELU = "leaky_relu"
    PRELU = "prelu"
    ELU = "elu"
    SELU = "selu"
    GELU = "gelu"
    SILU = "silu"
    MISH = "mish"
    TANH = "tanh"
    SIGMOID = "sigmoid"
    SOFTPLUS = "softplus"


class MotifName(StrEnum):
    RESIDUAL_STACK = "residual_stack"
    ENCODER = "encoder"
    DECODER = "decoder"
    BOTTLENECK = "bottleneck"
    MULTI_BRANCH = "multi_branch"
    FUSION = "fusion"
    MESSAGE_PASSING_STACK = "message_passing_stack"
